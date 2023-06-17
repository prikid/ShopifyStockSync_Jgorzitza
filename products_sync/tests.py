import os
import random
from pathlib import Path

import pandas as pd
from decouple import config
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIRequestFactory, APITestCase

from app import settings
from app.lib.shopify_client import ShopifyClient
from products_sync.sync_processors import Fuse5Processor, ShopifyProductsUpdater
from products_sync.sync_processors.shopify_products_updater import SHOPIFY_FIELDS


class ShopifyProductsUpdater_Patched(ShopifyProductsUpdater):

    def __init__(self, shopify_client: ShopifyClient, supplier_products_df: pd.DataFrame, source_name: str):
        super().__init__(shopify_client, supplier_products_df, source_name)
        supplier_products_df[SHOPIFY_FIELDS.price] += random.randint(0, 10)
        supplier_products_df[SHOPIFY_FIELDS.quantity] += random.randint(0, 10)


class TestShopifyProductsUpdater(APITestCase):
    def setUp(self):
        os.environ.setdefault('FUSE5_LOAD_DATA_FROM_FILE', 'samples/suppliers_data.csv')
        os.environ.setdefault('SHOPIFY_SHOP_NAME', 'prikidtest')

    def test_sync_full(self):
        processor = Fuse5Processor(
            dict(
                API_KEY=config("FUSE5_API_KEY"),
                API_URL=config("FUSE5_API_URL")
            ),
            updater_class=ShopifyProductsUpdater_Patched
        )

        processor.run_sync(dry=False)

    def test_download_csv(self):
        # Using the standard RequestFactory API to create a form POST request
        url = reverse('products_sync:logs-download-csv', args=(1,))
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # def test_dummy(self):
    #     from .models import Processors
    #     from products_sync.models import StockDataSource
    #
    #     cls_name = Fuse5Processor.__name__
    #     name = StockDataSource.objects.filter(processor=Processors.FUSE_5_PROCESSOR.value).first().name
    #     print(name)

    def test_check_csv(self):
        df = pd.read_csv(settings.BASE_DIR / Path(config('FUSE5_LOAD_DATA_FROM_FILE')))

        gdf = df.groupby('unit_barcode').agg(
            Count=('unit_barcode', 'count'),
            Locations=('location_name', list),
            ProductNames=('product_name', list),
            productNumbers=('product_number', list),
            lineCodes=('line_code', list),
            qty=('quantity_onhand', list),
            qtyAll=('all_location_qty_onhand', list)
        )

        # gdf = df.groupby('location_name').agg(
        #     Count=('location_name', 'count'),
        # )

        gdf = gdf[gdf['Count'] > 1]

        pd.set_option('display.max_rows', None)
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', None)

        print(gdf)
