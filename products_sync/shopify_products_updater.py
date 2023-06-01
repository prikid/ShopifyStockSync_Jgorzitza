import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from app.lib.shopify_client import ShopifyClient
import pandas as pd
from products_sync import logger


@dataclass
class ProductData:
    upc: str
    price: str
    qty: str


class AbstractShopifyProductsUpdater(ABC):
    @abstractmethod
    def __init__(self, supplier_products_df: pd.DataFrame = None):
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
        logger.info("Suppliers product found - %s", supplier_product)


if __name__ == '__main__':
    # for debug
    # TODO remove this

    from decouple import config
    import logging
    from products_sync import logger

    logging.basicConfig(format='%(asctime)s %(levelname)s:%(message)s', datefmt='%d-%m-%Y %I:%M:%S')
    logger.setLevel(logging.INFO)

    logger.info('Starting sync')

    shopify_client = ShopifyClient(
        shop_name=config('SHOPIFY_SHOP_NAME'),
        api_token=config('SHOPIFY_API_TOKEN'),
    )

    suppliers_df = pd.read_csv('../samples/suppliers_data.csv', dtype=str)
    updater = ShopifyProductsUpdater(shopify_client, suppliers_df)
    updater.process()
