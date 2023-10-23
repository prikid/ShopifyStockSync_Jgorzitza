from .base_products_sync_processor import BaseProductsSyncProcessor


class CustomCSVProcessor(BaseProductsSyncProcessor):
    PROCESSOR_NAME = "Custom CSV"

    def __init__(self, params: dict):
        super().__init__(params)

        from ..models import CustomCsvData
        self.supplier_products_queryset = CustomCsvData.objects.filter(custom_csv_id=self.params['custom_csv_id'])

    def update_from_remote(self):
        pass
