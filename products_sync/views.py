import pandas as pd
from celery.result import AsyncResult
from django.http import HttpResponse
from django.utils.text import slugify
from django.utils.timezone import now
from rest_framework import mixins, viewsets
from rest_framework.authentication import TokenAuthentication
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from django_cte import With

from .models import StockDataSource, ProductsUpdateLog
from .serializers import StockDataSourceSerializer, ProductsUpdateLogSerializer
from .tasks import sync_products


class StockDataSourceViewSet(mixins.ListModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
    serializer_class = StockDataSourceSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    queryset = StockDataSource.objects.order_by('id').all()

    @action(detail=True, methods=['post'])
    def run(self, request, pk=None, dry: bool = False):
        source = self.get_object()
        task = sync_products.delay(source.id, dry)

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

        task_meta = task._get_task_meta()
        state = task_meta["status"]

        logs = []
        gid = None

        result = task.get() if task.ready() else task_meta.get('result')
        if result is not None:
            logs = result.get('logs', [])
            gid = result.get('gid')

        # TODO use serializer
        return Response(dict(
            logs=logs[int(from_index):],
            gid=gid,
            state=state,
            complete=state in ['SUCCESS', 'FAILURE']
        ))

    def delete(self, request, task_id):
        """
        Stops the task

        :param request:
        :param task_id:
        :return:
        """

        task = sync_products.AsyncResult(task_id)
        task.abort()
        result = task.get()

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
