from django.urls import path, include
from rest_framework.routers import DefaultRouter

from products_sync import views

router = DefaultRouter()
router.register('sources', views.StockDataSourceViewSet)

app_name = 'products_sync'

urlpatterns = [
    path('', include(router.urls))
]
