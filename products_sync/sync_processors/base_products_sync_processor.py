from abc import ABC, abstractmethod
from typing import Type

from django.utils.functional import cached_property
import pandas as pd

from app import settings
from app.lib.shopify_client import ShopifyClient
from .shopify_products_updater import AbstractShopifyProductsUpdater
from .. import logger


class AbstractProductsSyncProcessor(ABC):
    def __init__(self, params: dict, updater_class: Type["AbstractShopifyProductsUpdater"]):
        self.params = params
        self.updater_class = updater_class

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

    # @abstractmethod
    # def save_to_db(self):
    #     pass

    # @abstractmethod
    # def update_store(self):
    #     pass


class BaseProductsSyncProcessor(AbstractProductsSyncProcessor):
    PROCESSOR_NAME = ''

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

        self.update_from_remote()

        if not check_if_aborted():
            return None

        logger.info('Starting %s products sync...' % self.PROCESSOR_NAME)

        shopify_client = self.get_shopify_client(check_if_aborted)

        updater = self.updater_class(shopify_client, self.source_name,
                                     update_price=kwargs.get('update_price', True),
                                     update_inventory=kwargs.get('update_inventory', True),
                                     )

        gid = updater.process(dry=dry).gid

        logger.info("%s products sync done!" % self.PROCESSOR_NAME)

        return gid

    def get_data(self) -> pd.DataFrame:
        raise NotImplemented
