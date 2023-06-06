import logging
import time

from celery.contrib.abortable import AbortableTask
from decouple import config

from app import celery
from products_sync import logger
from products_sync.models import StockDataSource
from products_sync.sync_processors import Fuse5Processor, get_processor_by_source
from products_sync.sync_processors.shopify_products_updater import ShopifyProductsUpdater


class CeleryLogHandler(logging.Handler):
    def __init__(self, level, task) -> None:
        super().__init__(level)
        self.task = task
        self._logs = []

    def emit(self, record):
        log_message = self.format(record)
        self._logs.append(log_message)

        # updating meta by logs and preserve state
        current_task = self.task.AsyncResult(self.task.request.id)
        self.task.update_state(
            state=current_task.state,
            meta=(current_task.result or {}) | {'logs': self._logs}
        )


@celery.task(bind=True, base=AbortableTask)
def sync_products(self_task, source_id: int):
    # TODO do not allow to put in queue or run a new task if the one is still running

    source = StockDataSource.objects.get(pk=source_id)

    handler = CeleryLogHandler(logging.DEBUG, self_task)
    formatter = logging.Formatter(fmt='%(asctime)s %(levelname)s:%(message)s', datefmt='%d-%m-%Y %I:%M:%S')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    try:
        processor = get_processor_by_source(source)
        processor.run_sync(is_aborted_callback=self_task.is_aborted)
    except Exception as e:
        logger.error(e)
        raise e
    finally:
        logger.removeHandler(handler)


@celery.task(bind=True)
def test_log(self_task):
    def text_generator(sleep_interval: int = 1):
        lines = [
            'Little brown lady',
            'Jumped into the blue water',
            'And smiled'
        ]
        start_time = time.time()
        while True:
            for line in lines:
                elapsed_time = int(time.time() - start_time)
                yield f"[{elapsed_time:>10} s] {line}\n"
                time.sleep(sleep_interval)
            yield "=========== Here we go again ===========\n"

    handler = CeleryLogHandler(logging.DEBUG, self_task)
    formatter = logging.Formatter(fmt='%(asctime)s %(levelname)s:%(message)s', datefmt='%d-%m-%Y %I:%M:%S')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    logger.info('Syncing products...')

    for i, msg in enumerate(text_generator(), 1):
        logger.info(msg)

        if i > 50:
            break

    logger.info('Products were synced!')
