from django.contrib import admin

from products_sync.models import StockDataSource


@admin.register(StockDataSource)
class StockDataSourcesAdmin(admin.ModelAdmin):
    list_display = ("name", "active")
    list_editable = ("active",)
    ordering = ['id']

