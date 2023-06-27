from typing import Type

from django.utils.functional import cached_property

from app import settings
from app.lib.fuse5_client import Fuse5Client
from app.lib.fuse5_csv import Fuse5CSV
from app.lib.shopify_client import ShopifyClient
from products_sync import logger
from products_sync.sync_processors.base_products_sync_processor import BaseProductsSyncProcessor
from products_sync.sync_processors.shopify_products_updater import AbstractShopifyProductsUpdater


class Fuse5Processor(BaseProductsSyncProcessor):
    """
    Sync products processor for Fuse 5
    http://oneguygarage.fuse5live.com/f5apidoc/standalone/#api-Product-Export_All_Products

    """

    # TODO use only fields from Fuse5FieldsMap
    FUSE5_EXPORT_CSV_FIELDS = [
        "line_code",
        "product_number",
        "product_name",
        "unit_barcode",
        "m1",
        "location_name",
        "quantity_onhand",
        # "all_location_qty_onhand"
    ]

    def __init__(self, params: dict, updater_class: Type["AbstractShopifyProductsUpdater"]):
        super().__init__(params, updater_class)

        assert 'API_KEY' in params, 'API_URL' in params
        self.fuse5csv = Fuse5CSV(fuse5_client=Fuse5Client(params['API_KEY'], params['API_URL']))
        self.updater_class = updater_class

    @cached_property
    def source_name(self):
        from products_sync.models import StockDataSource

        if source := StockDataSource.objects.filter(processor=self.__class__.__name__).first():
            return source.name
        else:
            return self.__class__.__name__

    def run_sync(self, dry: bool = False, is_aborted_callback: callable = None) -> int | None:
        def check_if_aborted():
            if is_aborted_callback and is_aborted_callback():
                logger.warning('The process has been aborted')
                return False
            return True

        suppliers_df = self.fuse5csv.get_data(update_from_remote=settings.FUSE5_UPDATE_CSV_FROM_REMOTE)

        if not check_if_aborted():
            return None

        logger.info('Starting Fuse5 products sync...')

        shopify_client = ShopifyClient(
            shop_name=settings.SHOPIFY_SHOP_NAME,
            api_token=settings.SHOPIFY_API_TOKEN,
            logger=logger,
            on_page_callback=check_if_aborted
        )

        # TODO maybe it is better to extract this logic to the parent class
        updater = self.updater_class(shopify_client, suppliers_df, self.source_name)
        gid = updater.process(dry=dry).gid

        logger.info("Fuse5 products sync done!")

        return gid
