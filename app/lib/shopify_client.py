from functools import cache
from http.client import IncompleteRead
from time import sleep
from typing import Type, Iterator, Iterable
import logging

import pandas as pd
from decouple import config
from pyactiveresource.connection import ClientError, ResourceNotFound

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

        self.locations: list = self.get_locations()
        self.default_location: Location = self.find_location_by_name(self.DEFAULT_LOCATION_NAME)
        if self.default_location is None:
            self.default_location = self.locations[0]

    def __del__(self):
        self.client.ShopifyResource.clear_session()

    def get_locations(self) -> list[Location]:
        return self.call_with_rate_limit(self.client.Location.find)

    @cache
    def find_location_by_name(self, location_name: str) -> Location | None:
        return next((loc for loc in self.locations if location_name in loc.name), None)

    @cache
    def find_location_by_id(self, location_id: int) -> Location | None:
        return next((loc for loc in self.locations if location_id == loc.id), None)

    def get_inventory_level(self, variant: Variant, location: Location | str | None = None) -> int:
        if location is None:
            location = self.default_location
        elif isinstance(location, str):
            location = self.find_location_by_name(location) or self.default_location

        try:
            inventory_level = self.call_with_rate_limit(
                self.client.InventoryLevel.find,
                location_ids=location.id,
                inventory_item_ids=variant.inventory_item_id,
                limit=1
            )[0]
        except IndexError:
            raise 'Unable to get the inventory level for the variant ID=%s and location `%s`' % (
                variant.id, location.name)

        return inventory_level.available

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

    def products(self, **params):
        return self._iter_objects(self.client.Product, **params)

    def variants(self):
        for variant in self._iter_objects(self.client.Variant):
            variant.price = float(variant.price)
            yield variant

    def orders(self, since_id: int = None, **params):
        if since_id is not None:
            params['since_id'] = since_id

        return self._iter_objects(self.client.Order, **params)

    def _iter_objects(self, resource: Type[ShopifyResource], **params) -> Iterator:
        total_objects_count = self.call_with_rate_limit(resource.count, **params)
        self.logger.info("The total %ss count is %s" % (resource.__name__.lower(), total_objects_count))

        objects = self.call_with_rate_limit(resource.find, limit=self.page_size, **params)
        pages = PaginatedIterator(objects)

        try:
            for page_idx, page in enumerate(pages):
                self.logger.info("Page %s containing %s %ss has been received from the Shopify store", page_idx + 1,
                                 len(page), resource.__name__.lower())

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

    def get_inventory_levels(self, inventory_item_ids: Iterable[int], location_ids: Iterable[int]) -> pd.DataFrame:
        inventory_levels = self.call_with_rate_limit(
            self.client.InventoryLevel.find,
            location_ids=','.join(map(str, location_ids)),
            inventory_item_ids=','.join(map(str, inventory_item_ids)),
            limit=self.page_size
        )

        return inventory_levels

    def get_variant(self, variant_id: int) -> Variant | None:
        if variant_id is None:
            return None
        try:
            return self.call_with_rate_limit(self.client.Variant.find, variant_id)
        except ResourceNotFound:
            return None
