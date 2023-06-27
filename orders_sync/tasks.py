from celery import shared_task
from celery_singleton import Singleton

from app import settings
from app.lib.shopify_client import ShopifyClient
from orders_sync import logger
from orders_sync.sync_processors.fuse_5_orders_sync_processor import Fuse5OrdersSyncProcessor, OrderStatuses


@shared_task(bind=True, base=Singleton, lock_expiry=60 * 60 * 4, name="Sync orders from Shopify to Fuse5")
def sync_orders(self_task, status: OrderStatuses = OrderStatuses.OPEN):
    processor = Fuse5OrdersSyncProcessor(
        params={
            'API_KEY': settings.FUSE5_API_KEY,
            'API_URL': settings.FUSE5_API_URL
        },
        shopify_client=ShopifyClient(
            shop_name=settings.SHOPIFY_SHOP_NAME,
            api_token=settings.SHOPIFY_API_TOKEN,
            logger=logger
            # on_page_callback=check_if_aborted
        )
    )

    gid = processor.run_sync(status=status)
    task = self_task.AsyncResult(self_task.request.id)
    results = task.result | {'gid': gid}
    return results
