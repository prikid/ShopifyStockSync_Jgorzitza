import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass

import pandas as pd

from app.lib.shopify_client import ShopifyClient
from products_sync import logger


@dataclass
class ProductData:
    upc: str
    price: str
    qty: str


class AbstractShopifyProductsUpdater(ABC):
    @abstractmethod
    def __init__(self, shopify_client: ShopifyClient, supplier_products_df: pd.DataFrame = None):
        self.shopify_client = shopify_client
        self.supplier_products_df: pd.DataFrame = supplier_products_df
        self.store_variants_df: pd.DataFrame | None = None

    @abstractmethod
    def process(self, dry: bool = True):
        return self


class ShopifyProductsUpdater(AbstractShopifyProductsUpdater):
    # FIELDS = ['id', 'product_id', 'price', 'barcode', 'sku', 'title', 'inventory_management',
    #           'inventory_quantity', 'inventory_item_id']

    RGX_SC_NUM = re.compile(r"\d+\.\d+E\+\d+")
    RGX_BARCODE = re.compile(r"\d{6,}")

    def __init__(self, shopify_client: ShopifyClient, supplier_products_df: pd.DataFrame = None):
        self.shopify_client = shopify_client
        self.supplier_products_df = supplier_products_df

    def process(self, dry: bool = True):
        """
        Fetch and iterate through all variants from Shopify, compare prices and quantity
        and update the item on shopify by new values
        """

        # TODO get only needed fields by API

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

                suppliers_products = self.supplier_products_df.query("upc==@variant.barcode")
                if not suppliers_products.empty:
                    s_product = suppliers_products.iloc[0].to_dict()
                    self._check_and_update(variant, s_product, dry=dry)

        return self

    def _check_and_update(self, shopify_variant, supplier_product, dry: bool):
        # TODO check price and qty and update

        df = pd.DataFrame([
            (shopify_variant.barcode, shopify_variant.sku, shopify_variant.price, shopify_variant.inventory_quantity),
            (supplier_product['upc'], supplier_product['product_number'], supplier_product['price'],
             supplier_product['quantity']),
        ], columns=['UPC', 'SKU', 'Price', 'Qty'], index=['Shopify:', 'Supplier:'])

        actions = ''
        if shopify_variant.price != supplier_product['price']:
            actions += f'The price will be updated to {supplier_product["price"]}\n'
        if shopify_variant.inventory_quantity != supplier_product['quantity']:
            actions += f'The quantity will be updated to {supplier_product["quantity"]}\n'

        if actions == '':
            actions = 'The product\'s price and qty is up to date.\n'

        if shopify_variant.sku == supplier_product['product_number']:
            log_level = logging.INFO
            msg = 'Matched products found'
        else:
            log_level = logging.WARNING
            msg = "Matched products found by UPC, but the SKU is different"

        logger.log(log_level, "%s: \n%s\n%s\n%s", msg, df, actions, '-' * 20)

#
# if __name__ == '__main__':
#     # for debug
#     # TODO remove this
#
#     from decouple import config
#     import logging
#     from products_sync import logger
#
#     logging.basicConfig(format='%(asctime)s %(levelname)s:%(message)s', datefmt='%d-%m-%Y %I:%M:%S')
#     logger.setLevel(logging.INFO)
#
#     logger.info('Starting sync')
#
#     shopify_client = ShopifyClient(
#         shop_name=config('SHOPIFY_SHOP_NAME'),
#         api_token=config('SHOPIFY_API_TOKEN'),
#     )
#
#     suppliers_df = pd.read_csv('../samples/suppliers_data.csv', dtype=str)
#     updater = ShopifyProductsUpdater(shopify_client, suppliers_df)
#     updater.process()
