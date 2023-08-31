from django.urls import path, include, re_path
from rest_framework.routers import DefaultRouter

from products_sync import views
from products_sync.views import UploadCustomCSVView

router = DefaultRouter()
router.register('sources', views.StockDataSourceViewSet)
router.register('products_sync_logs', views.ProductsUpdateLogViewSet, basename='products_sync_logs')
router.register('unmatched_review', views.UnmatchedProductsForReviewViewSet)

app_name = 'products_sync'

urlpatterns = [
    path('', include(router.urls)),
    re_path(r'^task/(?P<task_id>[\w-]+)/(?P<from_index>\d+)?', views.ManageCeleryTask.as_view()),
    path('upload-custom-csv/', UploadCustomCSVView.as_view(), name='upload_custom_csv')

]
