from rest_framework import serializers

from orders_sync.models import OrdersSyncLog


class OrdersSyncLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrdersSyncLog
        fields = '__all__'
