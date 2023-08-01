from rest_framework import serializers

from .models import StockDataSource, ProductsUpdateLog


class StockDataSourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockDataSource
        fields = ['id', 'name', 'active', 'processor']
        read_only_fields = ['id', 'name']


class ProductsUpdateLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductsUpdateLog
        fields = ['gid', 'source', 'time', 'sku', 'product_id', 'variant_id', 'barcode', 'changes']
        read_only_fields = fields

