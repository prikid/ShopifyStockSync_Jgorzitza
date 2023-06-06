from time import sleep
from typing import Type, Iterator
import logging

import shopify
from decouple import config
from shopify import ShopifyResource
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

        self.on_page_callback = on_page_callback

    def __del__(self):
        self.client.ShopifyResource.clear_session()

    def products(self):
        return self._iter_objects(self.client.Variant)

    def variants(self):
        return self._iter_objects(self.client.Variant)

    def _iter_objects(self, resource: Type[ShopifyResource]) -> Iterator:
        for page_idx, page in enumerate(PaginatedIterator(resource.find(limit=self.page_size))):
            self.logger.info("Page %s containing %s items has been received from the Shopify store", page_idx + 1,
                             len(page))

            for obj in page:
                yield obj

            if self.on_page_callback is not None:
                if not self.on_page_callback():
                    break

            req_count, rate = map(int, page.metadata['headers']['X-Shopify-Shop-Api-Call-Limit'].split('/'))

            if req_count == rate:
                self.logger.warning("The API rate limit has been exceeded. Waiting for %s seconds",
                                    self.RATE_LIMIT_WAIT_TIME)
                sleep(self.RATE_LIMIT_WAIT_TIME)
