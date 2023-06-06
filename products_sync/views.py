from celery.contrib.abortable import AbortableAsyncResult
from celery.result import AsyncResult
from rest_framework import mixins, viewsets
from rest_framework.authentication import TokenAuthentication
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import StockDataSource
from .serializers import StockDataSourceSerializer
from .tasks import sync_products


class StockDataSourceViewSet(mixins.ListModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
    serializer_class = StockDataSourceSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    queryset = StockDataSource.objects.all()

    @action(detail=True, methods=['post'])
    def run(self, request, pk=None, dry: bool = False):
        source = self.get_object()
        task = sync_products.delay(source.id)
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
        task_result = AsyncResult(task_id)

        task_meta = task_result._get_task_meta()

        state = task_meta["status"]

        logs = []
        if (result := task_meta.get('result', {})) is not None:
            logs = result.get('logs', [])

        return Response(dict(
            logs=logs[int(from_index):],
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

        # TODO stop the task gracefully
        # AsyncResult(task_id).revoke(terminate=True)
        AbortableAsyncResult(task_id).abort()

        sync_products.AsyncResult(task_id).abort()

        return Response('OK')
