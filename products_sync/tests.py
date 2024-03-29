import os
import random
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

import pandas as pd
from dateutil.utils import today
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from app import settings
from app.lib.shopify_client import ShopifyClient
from products_sync.sync_processors import Fuse5Processor, ShopifyProductsUpdater
from products_sync.models import Fuse5Products


class ShopifyProductsUpdater_Patched(ShopifyProductsUpdater):

    def __init__(self, shopify_client: ShopifyClient, source_name: str,
                 update_price: bool = True, update_inventory: bool = True):
        random.seed()

        # supplier_products_df[SHOPIFY_FIELDS.price] += random.randint(0, 10)
        # supplier_products_df[SHOPIFY_FIELDS.quantity] += random.randint(0, 10)

        super().__init__(shopify_client, source_name, update_price, update_inventory)


class TestShopifyProductsUpdater(APITestCase):
    def setUp(self):
        os.environ.setdefault('SHOPIFY_SHOP_NAME', 'prikidtest')
        settings.FUSE5_LOAD_DATA_CHANGED_SINCE = (today() - timedelta(days=10)).strftime("%m-%d-%Y 00:00:00")

    def mocked_update_from_remote(self):
        sample_fuse5_file = Path("samples/fuse5data.csv")
        self.save_csv_2_DB(sample_fuse5_file)

        product_1 = Fuse5Products.objects.get(pk=1)
        product_1.sku = 'CBT49'
        product_1.save(force_update=True)

        product_1 = Fuse5Products.objects.get(pk=2)
        product_1.sku = 'cbt49'
        product_1.save(force_update=True)

    # def mocked_find_by_sku(self, sku: str) -> pd.DataFrame:
    #     filtered_records = Fuse5Products.objects.filter(sku__iexact=sku)
    #     return self._get_found_df(filtered_records)

    @patch('app.lib.fuse5_remote.Fuse5DB.update_from_remote', new=mocked_update_from_remote)
    # @patch('app.lib.products_finder.ProductsFinder.find_by_sku', new=mocked_find_by_sku)
    def test_sync_full(self):
        processor = Fuse5Processor(
            dict(
                API_KEY=settings.FUSE5_API_KEY,
                API_URL=settings.FUSE5_API_URL
            ),
            updater_class=ShopifyProductsUpdater_Patched
        )

        processor.run_sync(dry=False)

    # def test_task_singleton(self):
    #     from tasks import sync_products
    #
    #     source = StockDataSource.objects.filter('')
    #     task1 = sync_products.delay(source.id, dry)

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
        df = pd.read_csv(settings.EXPORT_CSV_FILEPATH)

        df = df[df['inventory_quantity'] > 0]
        pd.set_option('display.max_rows', None)
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', None)
        print(df.head())

        return

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

    def test_iter_variants(self):
        shopify_client = ShopifyClient(
            shop_name=settings.SHOPIFY_SHOP_NAME,
            api_token=settings.SHOPIFY_API_TOKEN
        )

        for idx, variant in enumerate(shopify_client.variants(), 1):
            pass
