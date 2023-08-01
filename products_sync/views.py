import re

import pandas as pd
import redis
from celery.result import AsyncResult
from django.http import HttpResponse
from django.utils.text import slugify
from django.utils.timezone import now
from pyactiveresource import connection
from rest_framework import mixins, viewsets, status
from rest_framework.authentication import TokenAuthentication
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from django_cte import With

from app.settings import REDIS_URL
from . import logger
from .models import StockDataSource, ProductsUpdateLog, CustomCsvData
from .serializers import StockDataSourceSerializer, ProductsUpdateLogSerializer
from .tasks import sync_products

# Connect to the Redis server
redis_client = redis.from_url(REDIS_URL)


def convert_str_to_boolean(v: str):
    if v in ('False', 'false'):
        return False
    elif v in ('True', 'true'):
        return True

    return v


class StockDataSourceViewSet(mixins.ListModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
    serializer_class = StockDataSourceSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    queryset = StockDataSource.objects.order_by('id').all()

    @action(detail=True, methods=['post'])
    def run(self, request, pk=None, dry: bool = False):
        source = self.get_object()

        params = {k: convert_str_to_boolean(v) for k, v in request.query_params.items()}

        task = sync_products.delay(source.id, dry, params)

        return Response({'task_id': task.id})

    @action(detail=True, methods=['post'])
    def dryrun(self, request, pk=None):
        return self.run(request, pk=pk, dry=True)

    # @action(detail=True, methods=['get', 'post'])
    # def testlog(self, request, pk=None):
    #     # task = sync_products.delay()
    #     task = test_log.delay()
    #     return Response({'task_id': task.id})


class ManageCeleryTask(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, task_id, from_index):
        """
        Receives the latest logs for the task starting from the 'from_index'
        :param request:
        :param task_id:
        :param from_index:
        :return:
        """
        task = AsyncResult(task_id)
        state = task.state
        redis_key = f"task_logs:{task_id}"

        # Use LRANGE to get log items in the specified range
        logs = redis_client.lrange(redis_key, int(from_index), -1)

        # Decode the log items (assuming they are stored as UTF-8 strings)
        # logs = [item.decode('utf-8') for item in logs]

        gid = None
        err_message = ''
        status_code = status.HTTP_200_OK

        if (result := task.result) is not None:
            if isinstance(result, connection.Error):
                status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

                if m := re.search(r"code=(\d{3})", str(result)):
                    status_code = m[1]
            elif isinstance(result, AssertionError):
                status_code = status.HTTP_417_EXPECTATION_FAILED
                err_message = str(result)
            elif isinstance(result, dict):
                gid = result.get('gid')
            else:
                status_code = status.HTTP_417_EXPECTATION_FAILED
                err_message = "Got unexpected task result: %s" % str(result)

        if err_message:
            logger.error(err_message)

        # TODO use serializer
        return Response(dict(
            logs=logs,
            gid=gid,
            state=state,
            complete=task.ready(),
            err_message=err_message
        ), status=status_code)

    def delete(self, request, task_id):
        """
        Stops the task

        :param request:
        :param task_id:
        :return:
        """

        task = sync_products.AsyncResult(task_id)

        if not task.ready():
            task.abort()
            result = task.get()
        else:
            result = 'OK'

        # TODO use serializer
        return Response(result)


class ProductsUpdateLogViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = ProductsUpdateLogSerializer

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    queryset = ProductsUpdateLog.objects.all()

    @action(detail=False)
    def groups(self, request: Request) -> Response:
        # TODO paginating
        # first_rows = self.queryset.order_by('-gid', 'id').distinct('gid')

        cte = With(self.queryset.distinct('gid'))
        first_rows = cte.queryset().with_cte(cte).order_by('-gid', 'id')

        serializer = self.get_serializer(first_rows, many=True)
        return Response(serializer.data)

    @action(detail=False, url_path='download-csv/(?P<gid>\d+)/(?P<only_matched>[01])')
    def download_csv(self, request: Request, gid=None, only_matched=None):
        if only_matched is not None:
            only_matched = only_matched == '1'

        # getting only first row to create a filename
        queryset = self.queryset.filter(gid=gid).order_by('id')
        serializer = self.get_serializer(queryset.first())

        # TODO use dedicated serializer to extract data for CSV

        if not serializer.data:
            _time = now()
            _source = ''
        else:
            r = serializer.data
            _time = pd.to_datetime(r['time'])
            _source = r['source']

        _type = {True: '_updated', False: '_unmatched'}.get(only_matched, '')

        filename = slugify(
            "products_sync_log_%s_%s_%s%s" % (gid, _time.strftime("%d%m%Y%H%M"), _source, _type)
        )

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{filename}.csv"'
        response.headers['Access-Control-Expose-Headers'] = 'Content-Disposition'

        # now getting all rows
        if only_matched is True:
            queryset = queryset.exclude(changes__contains={'unmatched': True})
        elif only_matched is False:
            queryset = queryset.filter(changes__contains={'unmatched': True})

        serializer = self.get_serializer(queryset, many=True)
        df = pd.DataFrame(serializer.data, columns=ProductsUpdateLogSerializer.Meta.fields)
        if not df.empty:
            df['time'] = pd.to_datetime(df['time'])

            pd.json_normalize(df['changes'][0], sep='_')
            changes_df = pd.json_normalize(df['changes'], sep='_')

            df = pd.concat([df, changes_df], axis=1)

        # noinspection PyTypeChecker
        df.drop(
            columns=['gid', 'changes', 'unmatched'], errors='ignore'
        ).to_csv(
            response, index=False, date_format="%m-%d-%Y %H:%M:%S"
        )

        return response


class UploadCustomCSVView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # the frontend converts a csv file to a json object, and send it to backend as data, not as a file
        try:
            df = pd.DataFrame(request.data['csv'])

            for c in ('barcode', 'sku', 'location_name'):
                if c in df.columns:
                    df[c] = df[c].str.strip()

            if (c := 'price') in df.columns:
                df[c] = pd.to_numeric(df[c], downcast='float')

            if (c := 'inventory_quantity') in df.columns:
                df[c] = pd.to_numeric(df[c], downcast='integer')

            rec = CustomCsvData(data=df.to_dict())
            rec.save()

        except Exception as e:
            msg = "Unable to process CSV file"
            logger.error(msg + ' %s', e)
            return Response({'error': msg}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        CustomCsvData.delete_old()
        return Response({'custom_csv_data_id': rec.pk}, status=status.HTTP_201_CREATED)
