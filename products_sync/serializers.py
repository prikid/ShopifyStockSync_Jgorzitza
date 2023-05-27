from django.contrib.auth import authenticate
from rest_framework import serializers
from django.utils.translation import gettext_lazy as _

from .models import StockDataSource


class StockDataSourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockDataSource
        fields = ['id', 'name', 'active']
        read_only_fields = ['id', 'name']
