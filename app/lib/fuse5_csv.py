import logging
from datetime import datetime
from enum import Enum
from pathlib import Path

import pandas as pd

from app import settings
from app.lib.fuse5_client import Fuse5Client
from app.settings import EXPORT_CSV_FILEPATH


class BaseFieldsMap(Enum):
    BARCODE: tuple
    PRICE: tuple
    INVENTORY_QUANTITY: tuple
    SKU: tuple

    @classmethod
    def as_dict_flipped(cls) -> dict:
        return {item.value[0]: item.name.lower() for item in cls}

    @classmethod
    def dtypes(cls) -> dict:
        return {item.value[0]: item.value[1] for item in cls}

    @classmethod
    def fields(cls) -> list:
        return [item.name.lower() for item in cls]

    @classmethod
    def original_fields(cls) -> list:
        return [item.value[0] for item in cls]


class Fuse5FieldsMap(BaseFieldsMap):
    BARCODE = ('unit_barcode', str)
    PRICE = ('m1', float)
    INVENTORY_QUANTITY = ('quantity_onhand', int)
    SKU = ('product_number', str)
    LINE_CODE = ('line_code', str)
    PRODUCT_NAME = ('product_name', str)
    LOCATION_NAME = ('location_name', str)


class Fuse5CSV:
    FILEPATH = EXPORT_CSV_FILEPATH

    def __init__(self, fuse5_client: Fuse5Client, logger: logging.Logger = None):
        self.logger = logger or logging.getLogger(__name__)
        self.fuse5_client = fuse5_client

    @staticmethod
    def read_csv(path: str | Path = FILEPATH) -> pd.DataFrame:
        df = pd.read_csv(path, dtype=Fuse5FieldsMap.dtypes())
        columns = Fuse5FieldsMap.as_dict_flipped()
        df.rename(columns=columns, inplace=True)

        return df

    @classmethod
    def save_csv(cls, df: pd.DataFrame):
        cls.FILEPATH.parent.mkdir(exist_ok=True, parents=True)
        df.to_csv(cls.FILEPATH, index=False)

    @classmethod
    def exists(cls):
        return cls.FILEPATH.exists()

    def get_data(self, update_from_remote: bool = False) -> pd.DataFrame:
        if update_from_remote:
            # TODO use changed_since to get only items changed since previous sync
            suppliers_df = self.get_data_from_remote(
                changed_since=pd.to_datetime(settings.FUSE5_LOAD_DATA_CHANGED_SINCE)
            )
        else:
            if self.exists():
                self.logger.info("Loading data from file %s", self.FILEPATH.name)
                suppliers_df = self.read_csv()
            else:
                raise FileExistsError("The file %s not found", self.FILEPATH)

        return suppliers_df

    def get_data_from_remote(self, changed_since: datetime = None):
        self.logger.info("Loading suppliers data (may takes a few minutes)...")
        csv_url = self.fuse5_client.export_to_csv(Fuse5FieldsMap.original_fields(), changed_since=changed_since)

        self.logger.info('The file is ready. Downloading... - %s', csv_url)
        df = self.read_csv(csv_url)

        self.logger.info('Saving csv...')
        self.save_csv(df)

        return df
