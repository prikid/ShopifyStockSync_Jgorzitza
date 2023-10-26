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


class AbstractSupplierProducts(models.Model):
    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=["barcode"]),
            models.Index(fields=["sku"]),
        ]

    barcode = models.CharField(max_length=20, null=True)
    price = models.FloatField(null=True)
    inventory_quantity = models.IntegerField(null=True)
    sku = models.CharField(max_length=30, null=True)
    location_name = models.CharField(max_length=30, null=True)


class CustomCsv(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)

    @classmethod
    def delete_old(cls, days: int = 1):
        delete_time_point = today() - timedelta(days=days)
        cls.objects.filter(created_at__lte=delete_time_point).delete()


class CustomCsvData(AbstractSupplierProducts):
    custom_csv = models.ForeignKey(CustomCsv, on_delete=models.CASCADE)


class Fuse5Products(AbstractSupplierProducts):
    product_name = models.CharField(null=True)
    line_code = models.CharField(max_length=3, null=True)


class UnmatchedProductsForReview(models.Model):
    shopify_product_id = models.PositiveBigIntegerField()
    shopify_product_title = models.CharField(null=True)
    shopify_variant_id = models.PositiveBigIntegerField()
    shopify_sku = models.CharField(max_length=30, null=True)
    shopify_barcode = models.CharField(max_length=20, null=True)
    shopify_variant_title = models.CharField()

    possible_fuse5_products = models.JSONField()

    class Meta:
        unique_together = (('shopify_product_id', 'shopify_variant_id'),)
        indexes = [
            models.Index(fields=["shopify_sku"]),
            models.Index(fields=["shopify_barcode"]),
        ]

    def is_hidden(self):
        return HiddenProductsFromUnmatchedReview.objects.filter(
            shopify_product_id=self.shopify_product_id,
            shopify_variant_id=self.shopify_variant_id
        ).exists()


class HiddenProductsFromUnmatchedReview(models.Model):
    shopify_product_id = models.PositiveBigIntegerField()
    shopify_variant_id = models.PositiveBigIntegerField()

    class Meta:
        unique_together = (('shopify_product_id', 'shopify_variant_id'),)
