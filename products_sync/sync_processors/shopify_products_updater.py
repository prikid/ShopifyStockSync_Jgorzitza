import html
import json
import re
from abc import ABC, abstractmethod
from collections import namedtuple
from enum import StrEnum
from typing import Any

import pandas as pd
from django.db import connection, transaction
from django.db.models import QuerySet
from pyactiveresource.connection import ClientError
import more_itertools as mit

from app import settings
from app.lib.products_finder import ProductsFinder
from app.lib.shopify_client import ShopifyClient
from products_sync import logger
from shopify import Variant


class SHOPIFY_FIELDS(StrEnum):
    barcode = 'barcode'
    sku = 'sku'
    price = 'price'
    quantity = 'inventory_quantity'


class AbstractShopifyProductsUpdater(ABC):
    USE_CSV_FIELD_LOCATION = 'Use CSV field'

    @abstractmethod
    def __init__(self,
                 shopify_client: ShopifyClient,
                 source_name: str,
                 update_price: bool = True,
                 update_inventory: bool = True,
                 inventory_location: str = USE_CSV_FIELD_LOCATION,
                 check_if_aborted: callable = lambda: False
                 ):
        self.shopify_client: ShopifyClient
        self.source_name: str
        self.update_price: bool
        self.update_inventory: bool
        self.inventory_location: str | None
        self.store_variants_df: pd.DataFrame | None
        self.gid: int
        self.check_if_aborted: callable

    @abstractmethod
    def process(self, dry: bool = True):
        return self


class UpdateLogManager:
    # TODO use configurable fields instead of hardcoded

    def __init__(self, shopify_variant: Variant, supplier_product: dict, gid: int, source_name: str):
        from products_sync.models import ProductsUpdateLog

        self.shopify_variant_data: dict = shopify_variant.to_dict()
        self.supplier_product: dict = supplier_product

        self._log_item = ProductsUpdateLog(
            gid=gid,
            source=source_name,
            product_id=self.shopify_variant_data['product_id'],
            variant_id=self.shopify_variant_data['id'],
            sku=self.shopify_variant_data['sku'],
            barcode=self.shopify_variant_data['barcode'],
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
                 shopify_client: ShopifyClient, gid: int, source_name: str, update_price: bool = True,
                 update_inventory: bool = True
                 ):
        self.update_inventory = update_inventory
        self.update_price = update_price
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

        if self.update_price and not self.is_equal(SHOPIFY_FIELDS.price):
            self.do_update_price()

        if self.update_inventory and not self.is_equal(SHOPIFY_FIELDS.quantity, self.shopify_inventory_level):
            self.do_update_quantity(old_quantity=self.shopify_inventory_level)

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

    def do_update_price(self):
        if self.dry:
            self.add2log('The price will be updated to %s' % self.suppliers_product[SHOPIFY_FIELDS.price])
            self._updated = True
        else:
            self.shopify_variant.price = self.suppliers_product[SHOPIFY_FIELDS.price]
            if self.save_variant():
                # WARNING - at this point the 'price' field of shopify_variant becomes an str
                self.log_mngr.price_changed()
                self._updated = True

    def do_update_quantity(self, old_quantity: int = None):
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
                if isinstance(e, ClientError):
                    err_msg = str(json.loads(e.response.body).get('errors', {}))
                else:
                    err_msg = str(e)

                logger.error("Unable to update quantity of the shopify variant ID=%s - %s", self.shopify_variant.id,
                             err_msg)

            else:
                self.log_mngr.quantity_changed(location_name=res['location'].name, old_quantity=old_quantity)
                self._updated = True

    @property
    def comparing_text_table(self) -> str:
        shopify_variant_data = self.shopify_variant.to_dict()
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

    @classmethod
    def update_variant_field(cls, variant_id: int, field_name: str, new_value):
        shopify_client = ShopifyClient(
            shop_name=settings.SHOPIFY_SHOP_NAME,
            api_token=settings.SHOPIFY_API_TOKEN,
            logger=logger
        )

        shopify_variant = shopify_client.get_variant(variant_id)

        if not shopify_variant:
            raise Exception(f"Can't find variant with the ID={variant_id}")

        setattr(shopify_variant, field_name, new_value)

        if not shopify_client.save(shopify_variant):
            raise Exception("Can't save shopify variant")


# TODO use configurable fields instead of hardcoded
class ShopifyProductsUpdater(AbstractShopifyProductsUpdater):
    PER_PAGE = 250

    RGX_SC_NUM = re.compile(r"\d+\.\d+E\+\d+")
    RGX_BARCODE = re.compile(r"\d{6,}")

    MatchedProductsTuple = namedtuple('MatchedProductsTuple', 'shopify_variant suppliers_product')

    def __init__(self,
                 shopify_client: ShopifyClient,
                 source_name: str,
                 supplier_products: QuerySet,
                 update_price: bool = True,
                 update_inventory: bool = True,
                 inventory_location: str = AbstractShopifyProductsUpdater.USE_CSV_FIELD_LOCATION,
                 check_if_aborted: callable = lambda: False
                 ):
        """
        :param ShopifyClient shopify_client:
        :param supplier_products_df: Should contain all columns with names as in SHOPIFY_FIELDS
        """

        not_required = []
        if not update_price:
            not_required.append(SHOPIFY_FIELDS.price.value)
        if not update_inventory:
            not_required.append(SHOPIFY_FIELDS.quantity.value)

        # required_suppliers_fields = [item for item in list(SHOPIFY_FIELDS) if item not in not_required]
        #
        # assert all(map(supplier_products_df.columns.__contains__, required_suppliers_fields)), \
        #     f"Provided data should contain all of these columns - {','.join(required_suppliers_fields)}"

        self.source_name = source_name
        self.shopify_client = shopify_client
        self.update_price = update_price
        self.update_inventory = update_inventory
        self.inventory_location = None if inventory_location == self.USE_CSV_FIELD_LOCATION else inventory_location
        self._matched_products = []
        self._unmatched_variants = []
        self.gid = None
        self.check_if_aborted = check_if_aborted

        # TODO take location from the frontend
        self.products_finder = ProductsFinder(
            supplier_products,
            logger,
            default_location_name=self.inventory_location or self.shopify_client.DEFAULT_LOCATION_NAME
        )

    def process(self, dry: bool = True):
        """
        Fetch and iterate through all variants from Shopify, compare prices and quantity
        and update the item on shopify by new values
        """

        from products_sync.models import ProductsUpdateLog

        # TODO get only needed fields by API (have to solve issues with pagination when requesting specific fields)

        if not dry:
            try:
                self.gid = ProductsUpdateLog.objects.latest('gid').gid + 1
            except ProductsUpdateLog.DoesNotExist:
                self.gid = 1

            ProductsUpdateLog.delete_old(days=settings.PRODUCTS_SYNC_DELETE_LOGS_OLDER_DAYS)

        # receiving product variants from shopify and iterate them checking for matches
        for idx, variant in enumerate(self.shopify_client.variants(), 1):
            logger.debug("%s - Processing variant_id=%s, barcode=%s, price=%s, qty=%s", idx, variant.id,
                         variant.barcode, variant.price, variant.inventory_quantity)

            is_matched = False

            if variant.barcode:
                barcode = re.sub(r"\D", "", variant.barcode).strip()

                if self.RGX_SC_NUM.match(barcode):
                    barcode = str(int(float(barcode)))

                if self.RGX_BARCODE.match(barcode) is None:
                    logger.warning("The shopify barcode is invalid: %s", variant.barcode)
                    continue

                supplier_product = self.find_supplier_product(barcode, variant)

                if supplier_product:
                    is_matched = True
                    if self.update_price:
                        supplier_product['price'] = round(float(supplier_product['price']), 2)

                    if self.inventory_location:
                        supplier_product['location_name'] = self.inventory_location

                    self._matched_products.append(self.MatchedProductsTuple(variant, supplier_product))

                    if len(self._matched_products) >= self.PER_PAGE:
                        self._process_matched_products(dry)

            if not is_matched:
                supplier_products_by_sku = self.find_supplier_product_by_sku(variant)
                if supplier_products_by_sku:
                    self._unmatched_variants.append(self.MatchedProductsTuple(variant, supplier_products_by_sku))

                    logger.warning(
                        "Products matched by SKU, but not matched by BARCODE are found in the supplier's data: "
                        "product_id={product_id}; variant_id={id}; sku={sku}; barcode={barcode}. Found matches:"
                        " {matched}".format(
                            **variant.to_dict() | {
                                'matched': self._supplier_products_as_str(supplier_products_by_sku)})
                    )
                else:
                    self._unmatched_variants.append(self.MatchedProductsTuple(variant, None))
                    logger.warning(
                        "The matched product was not found in the supplier's data: "
                        "product_id={product_id}; variant_id={id}; sku={sku}; barcode={barcode} ".format(
                            **variant.to_dict())
                    )

        self._process_matched_products(dry)
        self._process_unmatched_products(dry)

        return self

    @staticmethod
    def _supplier_products_as_str(supplier_products: list | None) -> str:
        if supplier_products:
            return ', '.join(p.get('barcode') or html.unescape(p.get('product_name') or '') for p in supplier_products)

        return ''

    def _process_unmatched_products(self, dry: bool):
        if dry:
            return

        from products_sync.models import ProductsUpdateLog
        from products_sync.models import UnmatchedProductsForReview

        log_items = []
        unmatched_for_review_items = []
        for shopify_variant, supplier_products in self._unmatched_variants:

            if not self.check_if_aborted():
                return

            log_items.append(
                ProductsUpdateLog(
                    gid=self.gid,
                    source=self.source_name,
                    product_id=shopify_variant.product_id,
                    variant_id=shopify_variant.id,
                    sku=shopify_variant.sku,
                    barcode=shopify_variant.barcode,
                    changes=dict(
                        unmatched=True,
                        matched_by_sku=self._supplier_products_as_str(supplier_products),
                    )
                )
            )

            unmatched_for_review_items.append(
                UnmatchedProductsForReview(
                    shopify_product_id=shopify_variant.product_id,
                    shopify_variant_id=shopify_variant.id,
                    shopify_sku=shopify_variant.sku,
                    shopify_barcode=shopify_variant.barcode,
                    shopify_variant_title=shopify_variant.title,

                    possible_fuse5_products=supplier_products or []
                )
            )

        ProductsUpdateLog.objects.bulk_create(log_items, batch_size=1000)

        # extract product ids from unmatched variants
        required_product_ids = map(str, set(item.shopify_product_id for item in unmatched_for_review_items))

        unmatched_products_map = dict()
        for batch_ids in mit.batched(required_product_ids, self.PER_PAGE):
            # getting product titles for the ids from shopify
            unmatched_products_map.update(
                {
                    p.id: p.title
                    for p in self.shopify_client.products(ids=','.join(batch_ids), fields='id,title')
                }
            )

        # set product titles to variants
        for item in unmatched_for_review_items:
            item.shopify_product_title = unmatched_products_map.get(item.shopify_product_id)

        with transaction.atomic():
            # deleting all old records
            with connection.cursor() as cursor:
                cursor.execute(f"TRUNCATE TABLE {UnmatchedProductsForReview._meta.db_table}")

            # storing latest records
            UnmatchedProductsForReview.objects.bulk_create(
                unmatched_for_review_items,
                update_conflicts=True,
                unique_fields=['shopify_product_id', 'shopify_variant_id'],
                update_fields=['shopify_sku', 'shopify_product_title', 'shopify_barcode', 'shopify_variant_title',
                               'possible_fuse5_products'],
                batch_size=1000
            )

    def _process_matched_products(self, dry: bool):
        """
        We need to get inventory levels for all locations specified on supplier products,
        then if it is not the same update it for all matched products
        :return:
        """

        if not self._matched_products:
            return

        # grouping locations and inventory items to request inventory level from Shopify in one call
        required_location_names = set()
        required_inventory_items = dict()

        for shopify_variant, supplier_product in self._matched_products:
            required_location_names.add(supplier_product['location_name'])
            required_inventory_items[shopify_variant.inventory_item_id] = shopify_variant

        required_locations = dict()
        for loc_name in required_location_names:
            location = self.shopify_client.find_location_by_name(loc_name)

            if location is None:
                logger.warning(f'Inventory location `{loc_name}` not found in the Shopify store')
            else:
                required_locations[location.id] = loc_name

        if required_locations:

            # requesting inventory levels from Shopify
            inventory_levels_map = {
                (item.inventory_item_id, required_locations[item.location_id]): item.available
                for item in self.shopify_client.get_inventory_levels(required_inventory_items, required_locations)
            }

            while self._matched_products:

                if not self.check_if_aborted():
                    return

                shopify_variant, supplier_product = self._matched_products.pop()
                inventory_level = inventory_levels_map.get((shopify_variant.inventory_item_id,
                                                            supplier_product['location_name']))

                ShopifyVariantUpdater(
                    shopify_variant,
                    supplier_product,
                    shopify_inventory_level=inventory_level,
                    shopify_client=self.shopify_client,
                    gid=self.gid,
                    source_name=self.source_name,
                    update_price=self.update_price,
                    update_inventory=self.update_inventory
                )(dry=dry)

    def find_supplier_product(self, shopify_variant_barcode: str, shopify_variant: Variant) -> dict | None:
        shopify_variant_data = shopify_variant.to_dict() | {'barcode': shopify_variant_barcode}
        found_product = self.products_finder.find_product_by_barcode_and_sku(shopify_variant_data)

        return found_product

    def find_supplier_product_by_sku(self, shopify_variant: Variant) -> list[dict] | None:
        found_products = self.products_finder.find_products_by_sku(shopify_variant.to_dict())
        return found_products
