import logging
import tempfile
from abc import abstractmethod
from datetime import datetime
from enum import Enum
from html import unescape
from pathlib import Path
from typing import BinaryIO

import pandas as pd
import requests
from django.db import connection

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
    PRICE = ('m6', float)
    INVENTORY_QUANTITY = ('quantity_onhand', int)
    SKU = ('product_number', str)
    LINE_CODE = ('line_code', str)
    PRODUCT_NAME = ('product_name', str)
    LOCATION_NAME = ('location_name', str)


class Fuse5RemoteBase:
    def __init__(self, fuse5_client: Fuse5Client, logger: logging.Logger = None):
        self.logger = logger or logging.getLogger(__name__)
        self.fuse5_client = fuse5_client

    @staticmethod
    def _download_csv(url: str, save_to: Path | BinaryIO):
        response = requests.get(url)
        if response.ok:
            if isinstance(save_to, Path):
                save_to.write_bytes(response.content)
            else:
                save_to.write(response.content)

    def get_data_from_remote(self, save_to: Path | BinaryIO, changed_since: datetime = None):
        csv_url = self.get_csv_url_from_remote(changed_since)
        self._download_csv(csv_url, save_to)

    def get_csv_url_from_remote(self, changed_since):
        self.logger.info("Loading suppliers data (may takes a few minutes)...")
        csv_url = self.fuse5_client.export_to_csv(Fuse5FieldsMap.original_fields(), changed_since=changed_since)
        self.logger.info('The file is ready on the remote - %s', csv_url)

        return csv_url

    @abstractmethod
    def _read_data(self) -> pd.DataFrame:
        ...

    @abstractmethod
    def get_data(self, update_from_remote: bool = False) -> pd.DataFrame:
        ...

    @classmethod
    @abstractmethod
    def exists(cls):
        ...


class Fuse5CSV(Fuse5RemoteBase):
    FILEPATH = EXPORT_CSV_FILEPATH

    def _read_data(self) -> pd.DataFrame:
        df = pd.read_csv(self.FILEPATH, dtype=Fuse5FieldsMap.dtypes())
        columns = Fuse5FieldsMap.as_dict_flipped()
        df.rename(columns=columns, inplace=True)

        return df

    # @classmethod
    # def _save_data(cls, df: pd.DataFrame):
    #     cls.FILEPATH.parent.mkdir(exist_ok=True, parents=True)
    #     df.to_csv(cls.FILEPATH, index=False)

    @classmethod
    def exists(cls):
        return cls.FILEPATH.exists()

    def get_data(self, update_from_remote: bool = False) -> pd.DataFrame:
        if update_from_remote:
            # TODO use changed_since to get only items changed since previous sync
            self.get_data_from_remote(
                save_to=EXPORT_CSV_FILEPATH,
                changed_since=pd.to_datetime(settings.FUSE5_LOAD_DATA_CHANGED_SINCE)
            )
            suppliers_df = self._read_data()

        else:
            if self.exists():
                self.logger.info("Loading data from file %s", self.FILEPATH.name)
                suppliers_df = self._read_data()
            else:
                raise FileExistsError("The file %s not found", self.FILEPATH)

        return suppliers_df


class Fuse5DB(Fuse5RemoteBase):

    @classmethod
    def exists(cls):
        from products_sync.models import Fuse5Products

        return Fuse5Products.objects.exists()

    def _read_data(self) -> pd.DataFrame:
        from products_sync.models import Fuse5Products

        all_records = Fuse5Products.objects.all()
        df = pd.DataFrame(all_records.values()).set_index('id')

        return df

    def update_from_remote(self):
        with tempfile.NamedTemporaryFile(mode='wb', delete=True) as tmp_file:
            self.get_data_from_remote(
                save_to=tmp_file,
                changed_since=pd.to_datetime(settings.FUSE5_LOAD_DATA_CHANGED_SINCE)
            )
            self.save_csv_2_DB(Path(tmp_file.name))

    def get_data(self, update_from_remote: bool = False) -> pd.DataFrame:
        if update_from_remote:
            # TODO use changed_since to get only items changed since previous sync
            self.update_from_remote()

        self.logger.info("Loading suppliers data from DB")
        suppliers_df = self._read_data()

        return suppliers_df

    def save_csv_2_DB(self, csv_file_path: Path):
        from products_sync.models import Fuse5Products

        if not csv_file_path.exists() or csv_file_path.stat().st_size == 0:
            self.logger.warning("The suppliers CSV file doesn't exists or is empty")
            return

        table_name = Fuse5Products._meta.db_table
        with connection.cursor() as cursor:
            # read the csv file with pandas
            df = pd.read_csv(csv_file_path)

            # iterate over each column and apply html.unescape to convert entities like &amp; to text
            for col in df.columns:
                df[col] = df[col].apply(lambda x: unescape(x) if isinstance(x, str) else x)

            # overwrite the csv file with cleaned data
            df.to_csv(csv_file_path, index=False, header=True)

            copy_sql = """
                       COPY {table_name}({columns})
                       FROM stdin WITH CSV HEADER
                       DELIMITER as ','
                       """

            columns = ','.join([db_col for db_col in Fuse5FieldsMap.as_dict_flipped().values()])

            # drop all data before copying
            cursor.execute("TRUNCATE {table_name} RESTART IDENTITY".format(table_name=table_name))

            with csv_file_path.open() as f:
                cursor.copy_expert(
                    sql=copy_sql.format(table_name=table_name, columns=columns),
                    file=f
                )
