import logging

from celery import shared_task, chain
from celery.contrib.abortable import AbortableTask

from app import celery
from products_sync import logger
from products_sync.models import StockDataSource
from products_sync.sync_processors import get_processor_by_source


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


@shared_task(bind=True)
def run_all_sync_for_all_active_sources(self):
    source_ids = StockDataSource.objects.filter(active=True).values_list('id', flat=True)
    tasks = [sync_products.si(s_id, dry=False) for s_id in source_ids]

    task_chain = chain(tasks)
    task_chain.delay()


@shared_task(bind=True, base=AbortableTask)
def sync_products(self_task, source_id: int, dry: bool):
    # TODO do not allow to put in queue or run a new task if the one is still running

    source = StockDataSource.objects.get(pk=source_id)

    handler = CeleryLogHandler(logging.DEBUG, self_task)
    formatter = logging.Formatter(fmt='%(asctime)s %(levelname)s:%(message)s', datefmt='%d-%m-%Y %I:%M:%S')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    processor = get_processor_by_source(source)
    gid = processor.run_sync(dry=dry, is_aborted_callback=self_task.is_aborted)
    logger.removeHandler(handler)

    task = self_task.AsyncResult(self_task.request.id)
    results = task.result | {'gid': gid}
    return results

#
# @celery.task(bind=True)
# def test_log(self_task):
#     def text_generator(sleep_interval: int = 1):
#         lines = [
#             'Little brown lady',
#             'Jumped into the blue water',
#             'And smiled'
#         ]
#         start_time = time.time()
#         while True:
#             for line in lines:
#                 elapsed_time = int(time.time() - start_time)
#                 yield f"[{elapsed_time:>10} s] {line}\n"
#                 time.sleep(sleep_interval)
#             yield "=========== Here we go again ===========\n"
#
#     handler = CeleryLogHandler(logging.DEBUG, self_task)
#     formatter = logging.Formatter(fmt='%(asctime)s %(levelname)s:%(message)s', datefmt='%d-%m-%Y %I:%M:%S')
#     handler.setFormatter(formatter)
#     logger.addHandler(handler)
#
#     logger.info('Syncing products...')
#
#     for i, msg in enumerate(text_generator(), 1):
#         logger.info(msg)
#
#         if i > 50:
#             break
#
#     logger.info('Products were synced!')