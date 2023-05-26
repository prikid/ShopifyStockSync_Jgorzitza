from django.contrib import admin

from products_sync.models import StockDataSources


@admin.register(StockDataSources)
class StockDataSourcesAdmin(admin.ModelAdmin):
    pass
