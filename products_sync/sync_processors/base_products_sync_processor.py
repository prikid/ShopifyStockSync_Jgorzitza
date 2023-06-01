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
    def run_sync(self, dry: bool = False):
        """
        Runs the sync process
        :return:
        """
        pass

    @abstractmethod
    def get_logs(self) -> str:
        """
        Returns all logs generated during process
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


import logging

logging.basicConfig(filename='errors.log',
                    level=logging.ERROR,
                    filemode='w',
                    format='%(asctime)s %(levelname)s:%(message)s',
                    datefmt='%d-%m-%Y %I:%M:%S')

logging.error(f"Error happened")


class BaseProductsSyncProcessor(AbstractProductsSyncProcessor):
    def __init__(self, params: dict):
        super().__init__(params)

        self.stream = StringIO()
        handler = logging.StreamHandler(self.stream)
        formatter = logging.Formatter(fmt='%(asctime)s %(levelname)s:%(message)s', datefmt='%d-%m-%Y %I:%M:%S')
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    def __del__(self):
        # Remove the stream handler to avoid duplicate logs
        logger.removeHandler(self.stream)

    class FieldsMap(AbstractProductsSyncProcessor.FieldsMap):
        @classmethod
        def as_dict_flipped(cls):
            return {item.value[0]: item.name.lower() for item in cls}

        @classmethod
        def dtypes(cls):
            return {item.value[0]: item.value[1] for item in cls}

    def get_logs(self) -> list[str]:
        self.stream.seek(0)
        logs = self.stream.read().strip().split("\n")
        return logs

    def run_sync(self, dry: bool = False):
        raise NotImplemented

    def get_data(self) -> pd.DataFrame:
        raise NotImplemented

    #
    # def save_to_db(self):
    #     raise NotImplemented
    #
    # def update_store(self):
    #     raise NotImplemented
