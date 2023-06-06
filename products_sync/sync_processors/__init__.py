from .base_products_sync_processor import AbstractProductsSyncProcessor
from .fuse_5_processor import Fuse5Processor
from .custom_csv_processor import CustomCSVProcessor
from .shopify_products_updater import ShopifyProductsUpdater


def get_processor_by_source(source) -> AbstractProductsSyncProcessor:
    """

    :type source: StockDataSource
    """

    # module = importlib.import_module(__name__)
    # processor_class: Type["AbstractProductsSyncProcessor"] = getattr(module, source.processor)

    processor_class = globals().get(source.processor)

    processor = processor_class(source.params, updater_class=ShopifyProductsUpdater)

    return processor
