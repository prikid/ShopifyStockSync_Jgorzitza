import logging
from abc import ABC, abstractmethod
from enum import Enum
from io import StringIO

import pandas as pd

from products_sync import logger


class AbstractProductsSyncProcessor(ABC):
    def __init__(self, params: dict):
        self.params = params

    class FieldsMap(Enum):
        UPC: tuple
        PRICE: tuple
        QUANTITY: tuple

    @abstractmethod
    def run_sync(self, dry: bool = False, is_aborted_callback: callable = None):
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
    class FieldsMap(AbstractProductsSyncProcessor.FieldsMap):
        @classmethod
        def as_dict_flipped(cls):
            return {item.value[0]: item.name.lower() for item in cls}

        @classmethod
        def dtypes(cls):
            return {item.value[0]: item.value[1] for item in cls}

    def run_sync(self, dry: bool = False, is_aborted_callback: callable = None):
        raise NotImplemented

    def get_data(self) -> pd.DataFrame:
        raise NotImplemented

    #
    # def save_to_db(self):
    #     raise NotImplemented
    #
    # def update_store(self):
    #     raise NotImplemented
