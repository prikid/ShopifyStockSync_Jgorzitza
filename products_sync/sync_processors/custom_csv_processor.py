from .base_products_sync_processor import BaseProductsSyncProcessor
from .. import logger


class CustomCSVProcessor(BaseProductsSyncProcessor):

    def run_sync(self, dry: bool = False, is_aborted_callback: callable = None) -> int | None:
        logger.error('Not implemented yet')
        return None
