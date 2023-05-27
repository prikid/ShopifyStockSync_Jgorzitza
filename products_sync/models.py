from django.db import models
from django.utils.translation import gettext_lazy as _


class StockDataSource(models.Model):
    class Processors(models.TextChoices):
        FUSE_5_PROCESSOR = "FUSE_5", _("Fuse 5")
        CUSTOM_CSV_PROCESSOR = "CUSTOM_CSV", _("Custom CSV")

    name = models.CharField(max_length=30)
    active = models.BooleanField()
    processor = models.CharField(max_length=20, choices=Processors.choices)
    params = models.JSONField(blank=True, default=dict)

    def __str__(self):
        return self.name
