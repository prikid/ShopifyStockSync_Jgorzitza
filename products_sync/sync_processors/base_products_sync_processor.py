from abc import ABC, abstractmethod
from typing import Type

from django.db.models import QuerySet
from django.utils.functional import cached_property
import pandas as pd

from app import settings
from app.lib.shopify_client import ShopifyClient
from .shopify_products_updater import ShopifyProductsUpdater, AbstractShopifyProductsUpdater
from .. import logger


class AbstractProductsSyncProcessor(ABC):
    def __init__(self, params: dict):
        self.params = params

    @abstractmethod
    def run_sync(self, dry: bool = False, is_aborted_callback: callable = None, **kwargs) -> int | None:
        """
        Runs the sync process
        :return:
        """
        pass

    @abstractmethod
    def get_data(self) -> pd.DataFrame:
        """
       Fetches suppliers products data from the source and return as a DataFrame
       :return: pd.DataFrame
       """
        pass


class BaseProductsSyncProcessor(AbstractProductsSyncProcessor):
    PROCESSOR_NAME = ''

    def __init__(self, params: dict):
        super().__init__(params)
        self.updater_class: Type["AbstractShopifyProductsUpdater"] = ShopifyProductsUpdater

    @property
    def supplier_products_queryset(self) -> QuerySet | None:
        return None

    @cached_property
    def source_name(self):
        from products_sync.models import StockDataSource

        if source := StockDataSource.objects.filter(processor=self.__class__.__name__).first():
            return source.name
        else:
            return self.__class__.__name__

    @staticmethod
    def get_shopify_client(check_if_aborted: callable):
        return ShopifyClient(
            shop_name=settings.SHOPIFY_SHOP_NAME,
            api_token=settings.SHOPIFY_API_TOKEN,
            logger=logger,
            on_page_callback=check_if_aborted
        )

    def get_suppliers_df(self, *args, **kwargs) -> pd.DataFrame:
        raise NotImplemented

    def update_from_remote(self):
        raise NotImplemented

    def run_sync(self, dry: bool = False, is_aborted_callback: callable = None, **kwargs) -> int | None:
        def check_if_aborted():
            if is_aborted_callback and is_aborted_callback():
                logger.warning('The process has been aborted')
                return False
            return True

        if settings.FUSE5_UPDATE_CSV_FROM_REMOTE:
            self.update_from_remote()

        if not check_if_aborted():
            return None

        logger.info('Starting %s products sync...' % self.PROCESSOR_NAME)

        shopify_client = self.get_shopify_client(check_if_aborted)

        updater = self.updater_class(
            shopify_client=shopify_client,
            source_name=self.source_name,
            supplier_products=self.supplier_products_queryset,
            update_price=self.params.get('update_price', True),
            update_inventory=self.params.get('update_inventory', True),
            inventory_location=self.params.get('shopify_inventory_location', None),
            check_if_aborted=check_if_aborted
        )

        gid = updater.process(dry=dry).gid

        logger.info("%s products sync done!" % self.PROCESSOR_NAME)

        return gid

    def get_data(self) -> pd.DataFrame:
        raise NotImplemented
