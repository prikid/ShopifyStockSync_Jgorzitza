import importlib
from typing import Type

from rest_framework import mixins, viewsets
from rest_framework.authentication import TokenAuthentication
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from . import logger
from .models import StockDataSource
from .serializers import StockDataSourceSerializer
from .sync_processors import AbstractProductsSyncProcessor, get_processor_by_source


class StockDataSourceViewSet(mixins.ListModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
    serializer_class = StockDataSourceSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    queryset = StockDataSource.objects.all()

    @action(detail=True, methods=['post'])
    def run(self, request, pk=None, dry: bool = False):
        source = self.get_object()
        processor = get_processor_by_source(source)

        # Call the common interface method
        try:
            processor.run_sync(dry=dry)
        except Exception as e:
            raise e

        return Response({
            'success': True,
            'logs': processor.get_logs()
        })

    @action(detail=True, methods=['post'])
    def dryrun(self, request, pk=None):
        return self.run(request, pk=pk, dry=True)
