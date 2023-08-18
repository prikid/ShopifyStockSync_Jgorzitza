from typing import Type

import pandas as pd

from app import settings
from app.lib.fuse5_client import Fuse5Client
from app.lib.fuse5_remote import Fuse5DB
from products_sync import logger
from products_sync.sync_processors.base_products_sync_processor import BaseProductsSyncProcessor
from products_sync.sync_processors.shopify_products_updater import AbstractShopifyProductsUpdater


class Fuse5Processor(BaseProductsSyncProcessor):
    """
    Sync products processor for Fuse 5
    http://oneguygarage.fuse5live.com/f5apidoc/standalone/#api-Product-Export_All_Products

    """

    PROCESSOR_NAME = 'Fuse 5'

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
        self.fuse5data = Fuse5DB(
            fuse5_client=Fuse5Client(params['API_KEY'], params['API_URL']),
            logger=logger
        )


    def get_suppliers_df(self) -> pd.DataFrame:
        return self.fuse5data.get_data(update_from_remote=settings.FUSE5_UPDATE_CSV_FROM_REMOTE)

    # def run_sync(self, dry: bool = False, is_aborted_callback: callable = None) -> int | None:

