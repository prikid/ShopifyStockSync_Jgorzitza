from http.client import IncompleteRead
from time import sleep
from typing import Type, Iterator
import logging

from decouple import config
from pyactiveresource.connection import ClientError

import shopify
from shopify import ShopifyResource, Variant, Location, Limits
from shopify.collection import PaginatedIterator


class ShopifyClient:
    # RATE_LIMIT_WAIT_TIME = 30
    DEFAULT_LOCATION_NAME = "One Guy Garage"

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

        self.locations = self.get_locations()
        self.default_location = self.find_location_by_name(self.DEFAULT_LOCATION_NAME)
        if self.default_location is None:
            self.default_location = self.locations[0]

    def __del__(self):
        self.client.ShopifyResource.clear_session()

    def get_locations(self) -> list[Location]:
        return self.call_with_rate_limit(self.client.Location.find)

    def find_location_by_name(self, location_name: str) -> Location | None:
        return next((loc for loc in self.locations if location_name in loc.name), None)

    def set_inventory_level(self, variant: Variant, quantity: int, location: Location | str | None = None):
        if location is None:
            location = self.default_location
        elif isinstance(location, str):
            location = self.find_location_by_name(location) or self.default_location

        inventory_level = self.call_with_rate_limit(
            self.client.InventoryLevel.set,
            inventory_item_id=variant.inventory_item_id,
            location_id=location.id,
            available=quantity
        )

        return dict(location=location, inventory_level=inventory_level)

    def products(self):
        return self._iter_objects(self.client.Product)

    def variants(self):
        for variant in self._iter_objects(self.client.Variant):
            variant.price = float(variant.price)
            yield variant

    def _iter_objects(self, resource: Type[ShopifyResource]) -> Iterator:
        total_objects_count = self.call_with_rate_limit(resource.count)
        self.logger.info("The total %ss count is %s" % (resource.__name__.lower(), total_objects_count))
        objects = self.call_with_rate_limit(resource.find, limit=self.page_size)
        pages = PaginatedIterator(objects)

        try:
            for page_idx, page in enumerate(pages):
                self.logger.info("Page %s containing %s items has been received from the Shopify store", page_idx + 1,
                                 len(page))

                for obj in page:
                    yield obj

                    if self.callback is not None:
                        if not self.callback():
                            return
        except IncompleteRead as e:
            logging.error("%s. Sleeping for 5s ...", e)
            sleep(5)

    def save(self, object: ShopifyResource):
        return self.call_with_rate_limit(object.save)

    @staticmethod
    def call_with_rate_limit(method: callable, *args, **kwargs):
        max_retries = 5

        while max_retries:
            max_retries -= 1

            try:
                is_limit_maxed = Limits.credit_maxed()
            except Exception as e:
                is_limit_maxed = True
                logging.error(e)

            if is_limit_maxed:
                logging.debug("Rate limit maxed. Sleeping 1 sec")
                sleep(1)

            try:
                return method(*args, **kwargs)
            except ClientError as e:
                if e.code == 429:
                    continue
                raise e
