from abc import ABC, abstractmethod
from typing import Type

import pandas as pd

from .shopify_products_updater import AbstractShopifyProductsUpdater


class AbstractProductsSyncProcessor(ABC):
    def __init__(self, params: dict, updater_class: Type["AbstractShopifyProductsUpdater"]):
        self.params = params
        self.updater_class = updater_class

    @abstractmethod
    def run_sync(self, dry: bool = False, is_aborted_callback: callable = None) -> int | None:
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
    def run_sync(self, dry: bool = False, is_aborted_callback: callable = None) -> int | None:
        raise NotImplemented

    def get_data(self) -> pd.DataFrame:
        raise NotImplemented

    #
    # def save_to_db(self):
    #     raise NotImplemented
    #
    # def update_store(self):
    #     raise NotImplemented
