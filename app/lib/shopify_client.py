from time import sleep
from typing import Type, Iterator
import logging

from decouple import config

import shopify
from shopify import ShopifyResource, Variant, Location
from shopify.collection import PaginatedIterator


class ShopifyClient:
    RATE_LIMIT_WAIT_TIME = 30

    def __init__(self, shop_name: str, api_token: str, page_size: int = 250, logger: logging.Logger = None,
                 on_page_callback: callable = None) -> None:
        if logger:
            self.logger = logger
        else:
            self.logger = logging.getLogger(__name__)
            self.logger.setLevel(config('DJANGO_LOG_LEVEL'))

        self.page_size = page_size
        shop_url = f"{shop_name}.myshopify.com"
        api_version = '2023-04'
        session = shopify.Session(shop_url, api_version, api_token)
        shopify.ShopifyResource.activate_session(session)
        self.client = shopify

        self.callback = on_page_callback

    def __del__(self):
        self.client.ShopifyResource.clear_session()

    def set_inventory_level(self, variant: Variant, quantity: int, location: Location | None = None):
        if location is None:
            location = self.client.Location.find(limit=1)[0]

        self.client.InventoryLevel.set(
            inventory_item_id=variant.inventory_item_id,
            location_id=location.id,
            available=quantity
        )

    def products(self):
        return self._iter_objects(self.client.Product)

    def variants(self):
        for variant in self._iter_objects(self.client.Variant):
            variant.price = float(variant.price)
            yield variant

    def _iter_objects(self, resource: Type[ShopifyResource]) -> Iterator:
        for page_idx, page in enumerate(PaginatedIterator(resource.find(limit=self.page_size))):
            self.logger.info("Page %s containing %s items has been received from the Shopify store", page_idx + 1,
                             len(page))

            for obj in page:
                yield obj

                if self.callback is not None:
                    if not self.callback():
                        break

            req_count, rate = map(int, page.metadata['headers']['X-Shopify-Shop-Api-Call-Limit'].split('/'))

            if req_count == rate:
                self.logger.warning("The API rate limit has been exceeded. Waiting for %s seconds",
                                    self.RATE_LIMIT_WAIT_TIME)
                sleep(self.RATE_LIMIT_WAIT_TIME)
