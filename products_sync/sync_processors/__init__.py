from typing import Type

from .base_products_sync_processor import AbstractProductsSyncProcessor
from .fuse_5_processor import Fuse5Processor
from .custom_csv_processor import CustomCSVProcessor
from .shopify_products_updater import ShopifyProductsUpdater, AbstractShopifyProductsUpdater


def get_processor_by_source(source) -> Type["AbstractProductsSyncProcessor"]:
    """
    :type source: StockDataSource
    """

    processor_class = globals().get(source.processor)
    processor = processor_class(source.params)

    return processor
