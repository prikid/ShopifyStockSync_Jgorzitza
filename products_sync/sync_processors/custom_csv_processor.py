from io import StringIO

import pandas as pd
from django.db import transaction
from django.db import connection as db_connection
from django.db.models import QuerySet

from .base_products_sync_processor import BaseProductsSyncProcessor


class CustomCSVProcessor(BaseProductsSyncProcessor):
    PROCESSOR_NAME = "Custom CSV"

    def __init__(self, params: dict):
        super().__init__(params)

    @property
    def supplier_products_queryset(self) -> QuerySet | None:
        from ..models import CustomCsvData

        if 'custom_csv_id' in self.params:
            return CustomCsvData.objects.filter(custom_csv_id=self.params['custom_csv_id'])

        return None

    def update_from_remote(self):
        if self.supplier_products_queryset is None and 'csv_url' in self.params:
            df = pd.read_csv(self.params['csv_url'], dtype=str)
            fields_map = {v: k for k, v in self.params['fields_map'].items()}
            df.rename(columns=fields_map, inplace=True)
            self.params['custom_csv_id'] = self.saveCSV2DB(df[fields_map.values()])

    @classmethod
    def saveCSV2DB(cls, df: pd.DataFrame) -> int:
        from ..models import CustomCsvData, CustomCsv

        df = df.copy()

        for c in ('barcode', 'sku', 'location_name'):
            if c in df.columns:
                df[c] = df[c].str.strip()

        if (c := 'price') in df.columns:
            df[c] = pd.to_numeric(df[c], downcast='float')

        if (c := 'inventory_quantity') in df.columns:
            df[c] = pd.to_numeric(df[c], downcast='integer')

        with transaction.atomic():
            rec = CustomCsv()
            rec.save()
            df[CustomCsvData.custom_csv.field.column] = rec.id

            csv_buffer = StringIO()
            df.to_csv(csv_buffer, index=False, header=False)
            csv_buffer.seek(0)

            with db_connection.cursor() as cursor:
                cursor.copy_from(csv_buffer, CustomCsvData._meta.db_table, sep=',', columns=df.columns)

        CustomCsv.delete_old()

        return rec.pk
