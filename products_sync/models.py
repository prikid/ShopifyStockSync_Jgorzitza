from django.db import models
from django.utils.translation import gettext_lazy as _

from .sync_processors.custom_csv_processor import CustomCSVProcessor
from .sync_processors.fuse_5_processor import Fuse5Processor


class StockDataSource(models.Model):
    class Processors(models.TextChoices):
        FUSE_5_PROCESSOR = Fuse5Processor.__name__, _("Fuse 5")
        CUSTOM_CSV_PROCESSOR = CustomCSVProcessor.__name__, _("Custom CSV")

    name = models.CharField(max_length=30)
    active = models.BooleanField()
    processor = models.CharField(max_length=20, choices=Processors.choices)
    params = models.JSONField(blank=True, default=dict)

    def __str__(self):
        return self.name
