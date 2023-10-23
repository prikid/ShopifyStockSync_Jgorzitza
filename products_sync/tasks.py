import logging

import redis
from celery import shared_task, chain
from celery.contrib.abortable import AbortableTask
from celery_singleton import Singleton

from app.settings import REDIS_URL
from products_sync import logger
from products_sync.models import StockDataSource
from products_sync.sync_processors import get_processor_by_source

# Connect to the Redis server
redis_client = redis.from_url(REDIS_URL)


class CeleryLogHandler(logging.Handler):
    def __init__(self, level, task) -> None:
        super().__init__(level)
        self.task = task

    def emit(self, record):
        log_message = self.format(record)

        # Append the log message to the Redis list with the task ID as the key
        redis_key = f"task_logs:{self.task.request.id}"
        redis_client.rpush(redis_key, log_message)

        # Set expiration time for the Redis key (optional)
        redis_client.expire(redis_key, 3600)  # Set expiration time to 1 hour


class SingletonAbortableTask(AbortableTask, Singleton):
    pass


@shared_task(bind=True, name='Sync products from all sources')
def run_all_sync_for_all_active_sources(self):
    source_ids = StockDataSource.objects.filter(active=True).values_list('id', flat=True)
    tasks = [sync_products.si(s_id, dry=False) for s_id in source_ids]

    task_chain = chain(tasks)
    task_chain.delay()


@shared_task(bind=True, base=SingletonAbortableTask, lock_expiry=60 * 60 * 4,
             name="Sync products from the source by ID")
def sync_products(self_task, source_id: int, dry: bool, params=None):
    if params is None:
        params = {}

    source = StockDataSource.objects.get(pk=source_id)
    source.params.update(params)

    handler = CeleryLogHandler(logging.DEBUG, self_task)
    formatter = logging.Formatter(fmt='%(asctime)s %(levelname)s:%(message)s', datefmt='%d-%m-%Y %I:%M:%S')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    try:
        processor = get_processor_by_source(source)
        gid = processor.run_sync(dry=dry, is_aborted_callback=self_task.is_aborted)
    finally:
        logger.removeHandler(handler)

    return {'gid': gid}
