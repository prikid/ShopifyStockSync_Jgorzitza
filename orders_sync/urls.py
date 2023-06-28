from django.urls import path, include
from rest_framework.routers import DefaultRouter

from orders_sync import views

router = DefaultRouter()
router.register('orders_sync_logs', views.OrdersSyncLogViewSet, basename='orders_sync_logs')

app_name = 'orders_sync'

urlpatterns = [
    path('', include(router.urls)),
]
