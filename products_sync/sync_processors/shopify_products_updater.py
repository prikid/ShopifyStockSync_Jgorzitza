import re
import sqlite3
from abc import ABC, abstractmethod
from collections import namedtuple
from enum import StrEnum
from typing import Any

import pandas as pd

from app import settings
from app.lib.shopify_client import ShopifyClient
from products_sync import logger
from shopify import Variant


class SHOPIFY_FIELDS(StrEnum):
    barcode = 'barcode'
    sku = 'sku'
    price = 'price'
    quantity = 'inventory_quantity'


class AbstractShopifyProductsUpdater(ABC):
    @abstractmethod
    def __init__(self, shopify_client: ShopifyClient, supplier_products_df: pd.DataFrame, source_name: str):
        self.source_name = source_name
        self.shopify_client = shopify_client
        self.supplier_products_df: pd.DataFrame = supplier_products_df
        self.store_variants_df: pd.DataFrame | None = None
        self.gid: int

    @abstractmethod
    def process(self, dry: bool = True):
        return self


class UpdateLogManager:
    # TODO use configurable fields instead of hardcoded

    def __init__(self, shopify_variant: Variant, supplier_product: dict, gid: int, source_name: str):
        from products_sync.models import ProductsUpdateLog

        self.shopify_variant_data: dict = shopify_variant.attributes.copy()
        self.supplier_product: dict = supplier_product

        self._log_item = ProductsUpdateLog(
            gid=gid,
            source=source_name,
            product_id=self.shopify_variant_data['product_id'],
            variant_id=self.shopify_variant_data['id'],
            sku=self.shopify_variant_data['sku'],
            changes=dict()
        )

    def price_changed(self):
        self._log_item.changes.update(dict(
            price=dict(
                old=self.shopify_variant_data[SHOPIFY_FIELDS.price],
                new=self.supplier_product[SHOPIFY_FIELDS.price]
            )
        ))

    def quantity_changed(self, location_name: str, old_quantity: int = None):
        self._log_item.changes.update(dict(
            quantity=dict(
                location=location_name,
                old=self.shopify_variant_data[SHOPIFY_FIELDS.quantity] if old_quantity is None else old_quantity,
                new=self.supplier_product[SHOPIFY_FIELDS.quantity]
            )
        ))

    def save2db(self):
        self._log_item.save()

    def get_message(self) -> str | None:
        if self._log_item.changes:
            msg = "The variant (sku=%s, product_id=%s, variant id=%s) has been updated - " % (
                self._log_item.sku,
                self._log_item.product_id,
                self._log_item.variant_id
            )

            if 'price' in self._log_item.changes:
                msg += 'price: %s->%s; ' % (
                    self._log_item.changes['price']['old'],
                    self._log_item.changes['price']['new']
                )

            if 'quantity' in self._log_item.changes:
                msg += 'quantity: %s->%s (%s); ' % (
                    self._log_item.changes['quantity']['old'],
                    self._log_item.changes['quantity']['new'],
                    self._log_item.changes['quantity']['location'],

                )
            return msg


class ShopifyVariantUpdater:

    def __init__(self, shopify_variant: Variant, suppliers_product: dict, *, shopify_inventory_level: int,
                 shopify_client: ShopifyClient, gid: int, source_name: str
                 ):
        self.shopify_inventory_level = shopify_inventory_level
        self.shopify_client = shopify_client
        self.shopify_variant = shopify_variant
        self.suppliers_product = suppliers_product
        self.dry = True
        self._log = []
        self._updated = False

        self.log_mngr = UpdateLogManager(self.shopify_variant, self.suppliers_product, gid, source_name)

    def __call__(self, dry: bool):
        self.dry = dry

        if self.dry:
            self.add2log('Matched products found')
            self.add2log(self.comparing_text_table)

        if not self.is_equal(SHOPIFY_FIELDS.sku):
            self.add2log("WARNING! SKU is not equal for in the variant ID=%s" % self.shopify_variant.id)

        if not self.is_equal(SHOPIFY_FIELDS.price):
            self.update_price()

        if not self.is_equal(SHOPIFY_FIELDS.quantity, self.shopify_inventory_level):
            self.update_quantity(old_quantity=self.shopify_inventory_level)

        if self.dry and not self._updated:
            self.add2log('The product is up to date')
        elif not self.dry and self._updated:
            self.add2log(self.log_mngr.get_message())
            self.log_mngr.save2db()

        if self._log:
            logger.info('\n'.join(self._log))

    def add2log(self, msg: str | None):
        if msg:
            self._log.append(msg)

    def is_equal(self, field_name: str, shopify_value: Any = None):
        if shopify_value is None:
            shopify_value = getattr(self.shopify_variant, field_name)

        return shopify_value == self.suppliers_product[field_name]

    def update_price(self):
        if self.dry:
            self.add2log('The price will be updated to %s' % self.suppliers_product[SHOPIFY_FIELDS.price])
            self._updated = True
        else:
            self.shopify_variant.price = self.suppliers_product[SHOPIFY_FIELDS.price]
            if self.save_variant():
                # WARNING - at this point the 'price' field of shopify_variantbecomes an str
                self.log_mngr.price_changed()
                self._updated = True

    def update_quantity(self, old_quantity: int = None):
        if self.dry:
            self.add2log('The quantity will be updated to %s' % self.suppliers_product[SHOPIFY_FIELDS.quantity])
            self._updated = True
        else:
            try:
                res = self.shopify_client.set_inventory_level(
                    self.shopify_variant,
                    self.suppliers_product[SHOPIFY_FIELDS.quantity],
                    location=self.suppliers_product['location_name']
                )
            except Exception as e:
                logger.error("Unable to update quantity of the shopify variant ID=%s - %s", self.shopify_variant.id, e)
            else:
                self.log_mngr.quantity_changed(location_name=res['location'].name, old_quantity=old_quantity)
                self._updated = True

    @property
    def comparing_text_table(self) -> str:
        shopify_variant_data = self.shopify_variant.attributes
        shopify_variant_data[SHOPIFY_FIELDS.quantity] = self.shopify_inventory_level
        shopify_attrs = map(shopify_variant_data.__getitem__, SHOPIFY_FIELDS)
        supplier_attrs = map(self.suppliers_product.get, SHOPIFY_FIELDS)

        df = pd.DataFrame(
            [shopify_attrs, supplier_attrs],
            columns=['UPC', 'SKU', 'Price', 'Qty'],
            index=['Shopify:', 'Supplier:']
        )
        return str(df)

    def save_variant(self):
        try:
            if not self.shopify_client.save(self.shopify_variant):
                raise Exception("Can't save shopify variant")
        except Exception as e:
            logger.error("Unable to update shopify product variant ID=%s - %s", self.shopify_variant.id, e)
            return False

        return True


# TODO use configurable fields instead of hardcoded
class ShopifyProductsUpdater(AbstractShopifyProductsUpdater):
    RGX_SC_NUM = re.compile(r"\d+\.\d+E\+\d+")
    RGX_BARCODE = re.compile(r"\d{6,}")

    MatchedProductsTuple = namedtuple('MatchedProductsTuple', 'shopify_variant suppliers_product')

    def __init__(self, shopify_client: ShopifyClient, supplier_products_df: pd.DataFrame, source_name: str):
        """
        :param ShopifyClient shopify_client:
        :param supplier_products_df: Should contain all columns with names as in SHOPIFY_FIELDS
        """

        required_suppliers_fields = list(SHOPIFY_FIELDS) + ['location_name']
        assert all(map(supplier_products_df.columns.__contains__, required_suppliers_fields)), \
            f"The supplier_products_df should contain all these columns - {','.join(required_suppliers_fields)}"

        self.source_name = source_name
        self.shopify_client = shopify_client

        # using sqlite to improve search performance
        logger.info('Indexing suppliers data for search...')
        self.sqlite_conn = sqlite3.connect(':memory:')
        supplier_products_df.to_sql('supplier_products', self.sqlite_conn)
        self.sqlite_conn.execute("CREATE INDEX barcode_idx ON supplier_products (barcode)")

        self._matched_products = []
        self.gid = None

    def __del__(self):
        self.sqlite_conn.close()

    def process(self, dry: bool = True):
        """
        Fetch and iterate through all variants from Shopify, compare prices and quantity
        and update the item on shopify by new values
        """

        from products_sync.models import ProductsUpdateLog

        # TODO get only needed fields by API

        if not dry:
            try:
                self.gid = ProductsUpdateLog.objects.latest('gid').gid + 1
            except ProductsUpdateLog.DoesNotExist:
                self.gid = 1

            ProductsUpdateLog.delete_old(days=settings.PRODUCTS_SYNC_DELETE_LOGS_OLDER_DAYS)

        for idx, variant in enumerate(self.shopify_client.variants(), 1):
            logger.debug("%s - Processing variant_id=%s, barcode=%s, price=%s, qty=%s", idx, variant.id,
                         variant.barcode, variant.price, variant.inventory_quantity)

            if variant.barcode:
                variant.barcode = re.sub(r"\D", "", variant.barcode).strip()

                if self.RGX_SC_NUM.match(variant.barcode):
                    variant.barcode = str(int(float(variant.barcode)))

                if self.RGX_BARCODE.match(variant.barcode) is None:
                    # if not self.is_barcode_valid(variant.barcode):
                    logger.warning("The shopify barcode is invalid: %s", variant.barcode)
                    continue

                # s_time = time.monotonic()
                supplier_product = self.find_supplier_product(variant.barcode, variant.sku)
                # print(time.monotonic() - s_time)

                if supplier_product:
                    supplier_product['price'] = round(float(supplier_product['price']), 2)
                    self._matched_products.append(self.MatchedProductsTuple(variant, supplier_product))

                    if len(self._matched_products) >= 250:
                        self._process_matched_products(dry)

        self._process_matched_products(dry)
        logger.info("Done!")

        return self

    def _process_matched_products(self, dry: bool):
        """
        We need to get inventory levels for all locations specified on supplier products,
        then if it is not the same update it for all matched products
        :return:
        """

        # grouping locations and inventory items to request inventory level from Shopify in one call
        required_location_names = set()
        required_inventory_items = dict()

        for shopify_variant, supplier_product in self._matched_products:
            required_location_names.add(supplier_product['location_name'])
            required_inventory_items[shopify_variant.inventory_item_id] = shopify_variant

        required_locations = dict()
        for loc_name in required_location_names:
            location = self.shopify_client.find_location_by_name(loc_name) or self.shopify_client.default_location
            required_locations[location.id] = loc_name

        # requesting inventory levels from Shopify
        inventory_levels_map = {
            (item.inventory_item_id, required_locations[item.location_id]): item.available
            for item in self.shopify_client.get_inventory_levels(required_inventory_items, required_locations)
        }

        while self._matched_products:
            shopify_variant, supplier_product = self._matched_products.pop()
            inventory_level = inventory_levels_map.get((shopify_variant.inventory_item_id,
                                                        supplier_product['location_name']))

            ShopifyVariantUpdater(
                shopify_variant,
                supplier_product,
                shopify_inventory_level=inventory_level,
                shopify_client=self.shopify_client,
                gid=self.gid,
                source_name=self.source_name
            )(dry=dry)

    def find_supplier_product(self, barcode: str, sku: str = None) -> dict | None:
        query = "SELECT * FROM supplier_products WHERE barcode = ?"
        suppliers_products = pd.read_sql_query(query, self.sqlite_conn, params=[barcode])

        if suppliers_products.empty:
            return None

        supplier_product = suppliers_products.iloc[0]

        if sku is not None:
            narrowed_by_sku = suppliers_products[suppliers_products['sku'] == sku]
            if not narrowed_by_sku.empty:
                supplier_product = narrowed_by_sku.iloc[0]

        return supplier_product.to_dict()
