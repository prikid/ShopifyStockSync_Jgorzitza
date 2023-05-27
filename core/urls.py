from django.urls import path

from core.views import CreateTokenView

app_name = 'core'

urlpatterns = [
    path('token/', CreateTokenView.as_view(), name='token')
]
