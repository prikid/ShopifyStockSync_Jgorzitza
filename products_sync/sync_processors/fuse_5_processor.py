import json
from decimal import Decimal
from pathlib import Path
from typing import Type

import pandas as pd
import requests
from decouple import config
from django.utils.functional import cached_property

from app import settings
from app.lib.shopify_client import ShopifyClient
from products_sync import logger
from products_sync.sync_processors.base_products_sync_processor import BaseProductsSyncProcessor
from products_sync.sync_processors.shopify_products_updater import AbstractShopifyProductsUpdater


class Fuse5Processor(BaseProductsSyncProcessor):
    """
    Sync products processor for Fuse 5
    http://oneguygarage.fuse5live.com/f5apidoc/standalone/#api-Product-Export_All_Products
    """

    def __init__(self, params: dict, updater_class: Type["AbstractShopifyProductsUpdater"]):
        super().__init__(params, updater_class)

        assert 'API_KEY' in params, 'API_URL' in params
        self.api_key = params['API_KEY']
        self.api_url = params['API_URL']

        self.updater_class = updater_class

        self._timeout = 60 * 60 * 2

    class FieldsMap(BaseProductsSyncProcessor.FieldsMap):
        BARCODE = ('unit_barcode', str)
        PRICE = ('m1', float)
        INVENTORY_QUANTITY = ('quantity_onhand', int)
        SKU = ('product_number', str)

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

        if saved_data_file_name := config('FUSE5_LOAD_DATA_FROM_FILE', None):
            if (saved_data_file := settings.BASE_DIR / Path(saved_data_file_name)).exists():
                logger.info("Loading data from file %s", saved_data_file_name)
                suppliers_df = self._read_csv(saved_data_file)
            else:
                suppliers_df = self.get_data()
                saved_data_file.parent.mkdir(exist_ok=True, parents=True)
                suppliers_df.to_csv(saved_data_file, index=False)
        else:
            suppliers_df = self.get_data()

        if is_aborted_callback is not None and is_aborted_callback():
            logger.warning('The process has been aborted')
            return None

        logger.info('Starting sync...')

        shopify_client = ShopifyClient(
            shop_name=settings.SHOPIFY_SHOP_NAME,
            api_token=settings.SHOPIFY_API_TOKEN,
            logger=logger,
            on_page_callback=check_if_aborted
        )

        # TODO maybe it is better to extract this logic to the parent class
        updater = self.updater_class(shopify_client, suppliers_df, self.source_name)
        gid = updater.process(dry=dry).gid

        return gid

    def get_data(self):
        logger.info("Loading suppliers data (may takes a few minutes)...")

        res = requests.post(self.api_url, data={'data': json.dumps(self._request_data)}, timeout=self._timeout)
        res.raise_for_status()

        try:
            res_data = res.json()['services'][0]['response']
        except (KeyError, IndexError):
            raise Exception('Unexpected response from the Fuse 5 server', res.content)

        if res_data['status']:
            csv_url = res_data['data']
            logger.info('The file is ready. Downloading... - %s', csv_url)
            return self._read_csv(csv_url)

        # something went wrong
        messages = ' '.join(str(item) for item in res_data['msg'])
        raise Exception(messages, res.content)

    def _read_csv(self, path: str) -> pd.DataFrame:
        df = pd.read_csv(path, dtype=self.FieldsMap.dtypes())
        columns = self.FieldsMap.as_dict_flipped()
        df.rename(columns=columns, inplace=True)

        return df

    @property
    def _request_data(self):
        # TODO use only fields from FieldsMap
        # TODO use changedsince to get only items changed since previous sync

        return {
            "authenticate": {
                "apikey": self.api_key
            },
            "services": [
                {
                    "call": "product/export",
                    "params": [
                        "line_code",
                        "product_number",
                        "product_name",
                        "unit_barcode",
                        "m1",
                        "location_name",
                        "quantity_onhand",
                        "all_location_qty_onhand"
                    ],

                    # FIXME
                    # "identifier": {
                    #     "changedsince": "06-15-2023 00:00:00"
                    # }
                }

            ]
        }

# if __name__ == '__main__':
#     # TODO remove this
#     # for debug
#
#     processor = Fuse5Processor({
#         'API_KEY': config('FUSE5_API_KEY'),
#         'API_URL': config('FUSE5_API_URL'),
#     })
#
#     processor.run_sync()
#
