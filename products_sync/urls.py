from django.urls import path, include, re_path
from rest_framework.routers import DefaultRouter

from products_sync import views

router = DefaultRouter()
router.register('sources', views.StockDataSourceViewSet)
router.register('logs', views.ProductsUpdateLogViewSet, basename='logs')

app_name = 'products_sync'

urlpatterns = [
    path('', include(router.urls)),
    re_path(r'^task/(?P<task_id>[\w-]+)/(?P<from_index>\d+)?', views.ManageCeleryTask.as_view()),
]
pass
