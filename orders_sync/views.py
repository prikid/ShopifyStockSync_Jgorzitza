import pandas as pd
from django.http import HttpResponse
from django.utils.text import slugify
from rest_framework import mixins, viewsets
from rest_framework.authentication import TokenAuthentication
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from orders_sync.models import OrdersSyncLog
from orders_sync.serializers import OrdersSyncLogSerializer


class OrdersSyncLogViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = OrdersSyncLogSerializer

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    queryset = OrdersSyncLog.objects.all()

    @action(detail=False)
    def groups(self, request: Request) -> Response:
        # TODO paginating
        # TODO count created orders and show on frontend

        first_rows = self.queryset.order_by('-gid', 'id').distinct('gid')

        serializer = self.get_serializer(first_rows, many=True)
        return Response(serializer.data)

    @action(detail=False, url_path='download-csv/(?P<gid>\d+)')
    def download_csv(self, request: Request, gid=None):
        queryset = self.queryset.filter(gid=gid).order_by('id')
        serializer = self.get_serializer(queryset, many=True)

        response = HttpResponse(content_type='text/csv')

        # TODO use dedicated serializer to extract data for CSV

        df = pd.DataFrame(serializer.data)
        df['time'] = pd.to_datetime(df['time'])

        r = df.iloc[0]
        filename = slugify(
            "orders_sync_log_%s_%s" % (r['gid'], r['time'].strftime("%d%m%Y%H%M"))
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}.csv"'
        response.headers['Access-Control-Expose-Headers'] = 'Content-Disposition'

        # noinspection PyTypeChecker
        df.drop(columns=['gid']).to_csv(response, index=False, date_format="%m-%d-%Y %H:%M:%S")

        return response
