from rest_framework import serializers

from .models import StockDataSource


class StockDataSourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockDataSource
        fields = ['id', 'name', 'active']
        read_only_fields = ['id', 'name']
