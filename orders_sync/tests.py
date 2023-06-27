import datetime
import os
from pprint import pprint

import pandas as pd
from django.test import TestCase

from app import settings
from app.lib.fuse5_client import Fuse5Client
from app.lib.shopify_client import ShopifyClient
from orders_sync.sync_processors.fuse_5_orders_sync_processor import Fuse5OrdersSyncProcessor, OrderStatuses


# Create your tests here.
class TestFuse5OrdersSyncProcessor(TestCase):
    def setUp(self):
        os.environ.setdefault('SHOPIFY_SHOP_NAME', 'prikidtest')
        os.environ.setdefault('DJANGO_LOG_LEVEL', 'DEBUG')

        self.shopify_client = ShopifyClient(
            shop_name=settings.SHOPIFY_SHOP_NAME,
            api_token=settings.SHOPIFY_API_TOKEN,
            # logger=logger,
            # on_page_callback=check_if_aborted
        )

        self.fuse5 = Fuse5Client(settings.FUSE5_API_KEY, settings.FUSE5_API_URL)

    def test_run_sync(self):
        processor = Fuse5OrdersSyncProcessor(
            dict(
                API_KEY=settings.FUSE5_API_KEY,
                API_URL=settings.FUSE5_API_URL
            ),
            shopify_client=self.shopify_client
        )

        processor.run_sync(status=OrderStatuses.ANY)

    def test_create_order(self):
        # logging.basicConfig(level=logging.DEBUG)
        # {'sales_order_id': '341919', 'sales_order_number': 'S1-58272', 'tracking_number': ''}
        params = {
            'account_number': 'A146',
            # 'sales_order_track_id': '4642833956899',
            # "sales_order_id": "4642833956899",
            # "sales_order_number": "S1-58295",
            # 'sales_order_number': "1070",
            'customer_purchase_order_number': "1070-4642833956899",
            'sales_order_notes': 'Created by ShopifySync app. Shopify order 1070 (ID=4642833956899)',
            'sales_order_location': 'One Guy Garage Store 01',
            'products': [
                {
                    'line_code': 'DYL',
                    'product_number': '00108',
                    'quantity': 1,
                    # 'price': 3.99
                }
            ],
            'shipping_address': {
                'name': 'TEST ORDER',
                'phone': '4169882212',
                'street': '2249 Pineneedle Row, ',
                'pobox': None,
                'city': 'Mississauga',
                'state': 'Ontario',
                'county': None,
                'country': 'Canada',
                'code': 'L5C 1V4'
            },

            # 'price_override': {
            #     'subtotal': 660.0,
            #     'tax': 0.1,
            #     'discount': 0.0,
            #     'handling': 0.0,
            #     'shipping': 5.3,
            #     'total': 680.0
            # }
        }

        res = self.fuse5.create_sales_order(params)

        pprint(res)

        if 'sales_order_number' in res:
            order = self.fuse5.get_sales_order(res['sales_order_number'])
            pprint(order)

    def test_get_orders(self):
        for order in self.fuse5.get_sales_orders(account_number=settings.FUSE5_ACCOUNT_NUMBER):
            c_date = pd.to_datetime(order['sales_order_created_date'])
            if c_date.date() >= datetime.date(2023, 6, 25):
                pprint(order)

    def test_get_order_details(self):
        sales_order_number = 'S1-58272'
        sales_order_number = 'S1-58281'
        order = self.fuse5.get_sales_order(sales_order_number)
        print(order)
