import json
from typing import Type

import pandas as pd
import requests

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
        super().__init__(params)

        assert 'API_KEY' in params, 'API_URL' in params
        self.api_key = params['API_KEY']
        self.api_url = params['API_URL']
        self.csv_url = None

        self.updater_class = updater_class

        self._timeout = 600

    class FieldsMap(BaseProductsSyncProcessor.FieldsMap):
        UPC = ('unit_barcode', str)
        PRICE = ('m1', float)
        QUANTITY = ('all_location_qty_onhand', int)

    def run_sync(self, dry: bool = False, is_aborted_callback: callable = None):
        def check_if_aborted():
            if is_aborted_callback():
                logger.warning('The process has been aborted')
                return False
            return True

        logger.info("Loading suppliers data (may takes a few minutes)...")

        # fetching data from remote
        suppliers_df = self.get_data()

        # for debug
        # suppliers_df = pd.read_csv(settings.BASE_DIR / 'samples/suppliers_data.csv')
        # suppliers_df.to_csv(settings.BASE_DIR / 'samples/suppliers_data.csv', index=False)

        if is_aborted_callback is not None and is_aborted_callback():
            logger.warning('The process has been aborted')
            return

        logger.info('Starting sync...')

        shopify_client = ShopifyClient(
            shop_name=settings.SHOPIFY_SHOP_NAME,
            api_token=settings.SHOPIFY_API_TOKEN,
            logger=logger,
            on_page_callback=check_if_aborted
        )

        # TODO maybe it is better to extract this logic to the parent class
        updater = self.updater_class(shopify_client, suppliers_df)
        updater.process(dry=dry)

    def get_data(self):
        res = requests.post(self.api_url, data={'data': json.dumps(self._request_data)}, timeout=self._timeout)
        res.raise_for_status()

        try:
            res_data = res.json()['services'][0]['response']
        except (KeyError, IndexError):
            raise Exception('Unexpected response from the Fuse 5 server', res.content)

        if res_data['status']:
            self.csv_url = res_data['data']
            return self._read_csv()

        # something went wrong
        messages = ' '.join(str(item) for item in res_data['msg'])
        raise Exception(messages, res.content)

    def _read_csv(self) -> pd.DataFrame:
        df = pd.read_csv(self.csv_url, dtype=self.FieldsMap.dtypes())

        columns = self.FieldsMap.as_dict_flipped()

        df.rename(columns=columns, inplace=True)

        return df

    @property
    def _request_data(self):
        # TODO use only fields fro FieldsMap
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
                        "all_location_qty_onhand"
                    ],
                    # "identifier": {
                    #     "changedsince": "06-03-2023"  # FIXME
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
