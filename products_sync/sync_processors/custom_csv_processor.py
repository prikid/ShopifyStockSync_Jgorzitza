import pandas as pd

from .base_products_sync_processor import BaseProductsSyncProcessor


class CustomCSVProcessor(BaseProductsSyncProcessor):
    PROCESSOR_NAME = "Custom CSV"

    def get_suppliers_df(self, *args, **kwargs) -> pd.DataFrame:
        from ..models import CustomCsvData

        _id = kwargs['custom_csv_data_id']
        data = CustomCsvData.objects.get(pk=_id).data
        df = pd.DataFrame(data)
        return df


