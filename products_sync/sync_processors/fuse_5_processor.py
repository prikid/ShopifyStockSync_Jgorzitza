import json

import pandas as pd

from app import settings
from app.lib.shopify_client import ShopifyClient
from products_sync import logger
from products_sync.shopify_products_updater import ShopifyProductsUpdater
from products_sync.sync_processors.base_products_sync_processor import BaseProductsSyncProcessor
import requests


class Fuse5Processor(BaseProductsSyncProcessor):
    """
    Sync products processor for Fuse 5
    http://oneguygarage.fuse5live.com/f5apidoc/standalone/#api-Product-Export_All_Products
    """

    def __init__(self, params: dict):
        super().__init__(params)

        assert 'API_KEY' in params, 'API_URL' in params
        self.api_key = params['API_KEY']
        self.api_url = params['API_URL']
        self.csv_url = None

        self._timeout = 600

    class FieldsMap(BaseProductsSyncProcessor.FieldsMap):
        UPC = ('unit_barcode', str)
        PRICE = ('m1', float)
        QUANTITY = ('all_location_qty_onhand', int)

    def run_sync(self, dry: bool = False):
        logger.info("Loading suppliers data...")

        suppliers_df = self.get_data()

        # TODO remove this
        suppliers_df.to_csv(settings.BASE_DIR / 'samples/suppliers_data.csv', index=False)

        logger.info('Starting sync...')

        shopify_client = ShopifyClient(
            shop_name=settings.SHOPIFY_SHOP_NAME,
            api_token=settings.SHOPIFY_API_TOKEN,
        )

        updater = ShopifyProductsUpdater(shopify_client, suppliers_df)
        updater.process(dry=dry)

        logger.info('Done')

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
                    #     "changedsince": "05-25-2023"  # FIXME
                    # }
                }

            ]
        }


if __name__ == '__main__':
    # TODO remove this
    # for debug

    processor = Fuse5Processor({
        'API_KEY': 'X5gO21dzMu6kUhaSCep42wiIpmWHfuVr',
        'API_URL': 'http://oneguygarage.fuse5live.com/f5api/'
    })

    processor.run_sync()

    # df = processor.get_data()
    # df.to_csv('../../samples/suppliers_data.csv', index=False)
