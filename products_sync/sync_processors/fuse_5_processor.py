import pandas as pd
from django.db.models import QuerySet

from app import settings
from app.lib.fuse5_client import Fuse5Client
from app.lib.fuse5_remote import Fuse5DB
from products_sync import logger
from products_sync.sync_processors.base_products_sync_processor import BaseProductsSyncProcessor


class Fuse5Processor(BaseProductsSyncProcessor):
    """
    Sync products processor for Fuse 5
    http://oneguygarage.fuse5live.com/f5apidoc/standalone/#api-Product-Export_All_Products

    """

    PROCESSOR_NAME = 'Fuse 5'

    # TODO use only fields from Fuse5FieldsMap
    FUSE5_EXPORT_CSV_FIELDS = [
        "line_code",
        "product_number",
        "product_name",
        "unit_barcode",
        "m1",
        "location_name",
        "quantity_onhand",
        # "all_location_qty_onhand"
    ]

    def __init__(self, params: dict):
        super().__init__(params)

        assert 'API_KEY' in params, 'API_URL' in params
        self.fuse5data = Fuse5DB(
            fuse5_client=Fuse5Client(params['API_KEY'], params['API_URL']),
            logger=logger
        )

    @property
    def supplier_products_queryset(self) -> QuerySet | None:
        from products_sync.models import Fuse5Products
        return Fuse5Products.objects

    def update_from_remote(self):
        self.fuse5data.update_from_remote()

    def get_suppliers_df(self) -> pd.DataFrame:
        return self.fuse5data.get_data(update_from_remote=settings.FUSE5_UPDATE_CSV_FROM_REMOTE)
