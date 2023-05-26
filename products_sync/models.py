from django.db import models
from django.utils.translation import gettext_lazy as _


class StockDataSources(models.Model):
    class Processors(models.Choices):
        FUSE_5_PROCESSOR = "FUSE_5", _("Fuse 5")
        CUSTOM_CSV_PROCESSOR = "CUSTOM_CSV", _("Custom csv")

    name = models.CharField(max_length=30)
    active = models.BooleanField()
    processor = models.CharField(choices=Processors.choices)
    params = models.JSONField()
