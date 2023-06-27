from datetime import timedelta

from dateutil.utils import today
from django.db import models


class OrdersSyncLog(models.Model):
    gid = models.PositiveBigIntegerField(db_index=True)
    time = models.DateTimeField(auto_now_add=True)

    fuse5_account_number = models.CharField()
    fuse5_sales_order_number = models.CharField()
    fuse5_sales_order_id = models.CharField()
    fuse5_customerpo = models.CharField()

    shopify_order_id = models.PositiveBigIntegerField()
    shopify_order_number = models.CharField()

    def __str__(self):
        return "{time}: {fuse5_customerpo} - {fuse5_sales_order_id}({fuse5_sales_order_number})".format(
            **self.__annotations__)

    @classmethod
    def delete_old(cls, days: int):
        # TODO do not delete parts of groups with the same gid. Only delete whole groups.
        delete_time_point = today() - timedelta(days=days)
        cls.objects.filter(time__lte=delete_time_point).delete()
