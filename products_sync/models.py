from datetime import timedelta

from dateutil.utils import today
from django.db import models
from django.utils.translation import gettext_lazy as _
from django_cte import CTEManager

from .sync_processors.custom_csv_processor import CustomCSVProcessor
from .sync_processors.fuse_5_processor import Fuse5Processor


class Processors(models.TextChoices):
    FUSE_5_PROCESSOR = Fuse5Processor.__name__, _(Fuse5Processor.PROCESSOR_NAME)
    CUSTOM_CSV_PROCESSOR = CustomCSVProcessor.__name__, _(CustomCSVProcessor.PROCESSOR_NAME)


class StockDataSource(models.Model):
    name = models.CharField(max_length=30)
    active = models.BooleanField()
    processor = models.CharField(max_length=20, choices=Processors.choices)
    params = models.JSONField(blank=True, default=dict)

    def __str__(self):
        return self.name


class ProductsUpdateLog(models.Model):
    objects = CTEManager()

    gid = models.PositiveBigIntegerField(db_index=True)
    source = models.CharField(max_length=30)
    time = models.DateTimeField(auto_now_add=True)
    sku = models.CharField()
    product_id = models.PositiveBigIntegerField(null=True)
    variant_id = models.PositiveBigIntegerField()
    barcode = models.CharField(max_length=20, null=True)
    changes = models.JSONField()

    def __str__(self):
        return "{time}: {title}({variant_id}) - {changes}".format(**self.__annotations__)

    @classmethod
    def delete_old(cls, days: int):
        # TODO do not delete parts of groups with the same gid. Only delete whole groups.
        delete_time_point = today() - timedelta(days=days)
        cls.objects.filter(time__lte=delete_time_point).delete()


class CustomCsvData(models.Model):
    data = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    @classmethod
    def delete_old(cls, days: int = 1):
        delete_time_point = today() - timedelta(days=days)
        cls.objects.filter(created_at__lte=delete_time_point).delete()

# class Fuse5Products(models.Model):
#     line_code = models.CharField(max_length=3)
#     product_number = models.CharField(max_length=30)
#     product_name = models.CharField()
#     unit_barcode = models.CharField(max_length=20)
#     m1 = models.FloatField()
#     location_name = models.CharField(max_length=30)
#     quantity_onhand = models.PositiveIntegerField()
#     # all_location_qty_onhand = models.PositiveIntegerField()
