import os

from celery import Celery
from celery.signals import worker_ready
from celery_singleton import clear_locks

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')

celery = Celery('app')
celery.config_from_object('django.conf:settings', namespace='CELERY')
celery.autodiscover_tasks()


@worker_ready.connect
def unlock_all(**kwargs):
    clear_locks(celery)
