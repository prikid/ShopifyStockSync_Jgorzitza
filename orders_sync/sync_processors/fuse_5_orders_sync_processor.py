from enum import StrEnum

from pydantic import BaseModel

from app import settings
from app.lib.fuse5_client import Fuse5Client
from app.lib.fuse5_remote import Fuse5DB
from app.lib.products_finder import ProductsFinder
from app.lib.shopify_client import ShopifyClient
from orders_sync import logger
from orders_sync.models import OrdersSyncLog
from shopify import Order


class Fuse5ShippingAddress(BaseModel):
    name: str | None
    phone: str | None
    street: str | None
    pobox: str | None
    city: str | None
    state: str | None
    county: str | None
    country: str | None
    code: str | None
    note: str | None

    @classmethod
    def from_shopify_order(cls, shopify_order: Order):
        if a := shopify_order.shipping_address:
            return cls(
                name=a.name,
                phone=a.phone,
                street=", ".join([a.address1 or '', a.address2 or '']),
                city=a.city,
                state=a.province,
                country=a.country,
                code=a.zip
            )


class Fuse5Product(BaseModel):
    line_code: str
    product_number: str
    quantity: int
    price: float

    # product_name: str
    # comment: :str
    # core_price: "0.00",
    # sell_price: "110.49",
    # subtotal: "110.49",
    # quantity: "1"


class OrderStatuses(StrEnum):
    OPEN = 'open'
    CLOSED = 'closed'
    CANCELLED = 'cancelled'
    ANY = 'any'


class Fuse5OrdersSyncProcessor:
    ORDER_ID_PREFIX = "shopify"

    def __init__(self, params: dict, shopify_client: ShopifyClient):
        assert 'API_KEY' in params, 'API_URL' in params

        self.shopify_client = shopify_client

        self.fuse5_account_number = settings.FUSE5_ACCOUNT_NUMBER
        self.fuse5 = Fuse5Client(params['API_KEY'], params['API_URL'])
        self.fuse5_locations = self.fuse5.get_locations()
        self.fuse5_default_location = next(iter(self.fuse5_locations), None)

        self.fuse5data = Fuse5DB(fuse5_client=self.fuse5, logger=logger)
        # self.fuse5data.update_from_remote()

        # update_from_remote = settings.FUSE5_UPDATE_CSV_FROM_REMOTE and not self.fuse5data.exists()
        # self.products_finder = SqliteProductsFinder(
        #     df=self.fuse5csv.get_data(update_from_remote=update_from_remote),
        #     logger=logger
        # )

        self.products_finder = ProductsFinder(logger, self.fuse5_default_location)

    def run_sync(self, since_id: int = None, status: OrderStatuses = OrderStatuses.OPEN):
        logger.info('Starting orders sync...')

        try:
            gid = OrdersSyncLog.objects.latest('gid').gid + 1
        except OrdersSyncLog.DoesNotExist:
            gid = 1

        OrdersSyncLog.delete_old(days=settings.ORDERS_SYNC_DELETE_LOGS_OLDER_DAYS)

        for order in self.shopify_client.orders(since_id, status=status):
            if self.is_order_exists(order):
                logger.debug("The order %s is already exists", self.get_customer_order_id(order))
            else:
                fuse5_order_info = self.create_order(order)
                if fuse5_order_info:
                    self.save_db_log(order, fuse5_order_info, gid)

        logger.info("Orders sync done!")

        return gid

    def save_db_log(self, shopify_order: Order, fuse5_order_info: dict, gid: int):
        OrdersSyncLog(
            gid=gid,

            fuse5_account_number=self.fuse5_account_number,
            fuse5_sales_order_number=fuse5_order_info['sales_order_number'],
            fuse5_sales_order_id=fuse5_order_info['sales_order_id'],
            fuse5_customerpo=self.get_customer_order_id(shopify_order),

            shopify_order_id=shopify_order.id,
            shopify_order_number=shopify_order.order_number
        ).save()

    def is_order_exists(self, shopify_order: Order):
        return self.fuse5.search_sales_order_by_customer_order_id(
            account_number=self.fuse5_account_number,
            customer_order_id=self.get_customer_order_id(shopify_order)
        ) is not None

    def get_customer_order_id(self, shopify_order: Order) -> str:
        return f"{self.ORDER_ID_PREFIX}-{shopify_order.order_number}-{shopify_order.id}"

    def create_order(self, shopify_order: Order) -> dict | None:
        order_id_msg = "%s (ID=%s)" % (shopify_order.order_number, shopify_order.id)

        products = self.find_matched_products(shopify_order, as_dict=True)

        if not products:
            logger.warning("Unable to create order %s because no products were found for it", order_id_msg)
            return None

        elif len(products) < len(shopify_order.line_items):
            logger.warning("Some products were not found for the order %s", order_id_msg)

        params = {
            "account_number": self.fuse5_account_number,

            # This doesn't work despite that described in docs
            # "sales_order_track_id": self.get_customer_order_id(shopify_order),
            # "sales_order_number": shopify_order.order_number,

            'customer_purchase_order_number': self.get_customer_order_id(shopify_order),
            'sales_order_notes': 'Created by ShopifySync app. Shopify order %s' % order_id_msg,

            # if not passed it will use the default for Fuse5 account billing address
            # "billing_address": {},

            "products": products
        }

        # if not passed it will use the default for Fuse5 account shipping address
        if shipping_address := Fuse5ShippingAddress.from_shopify_order(shopify_order):
            params['shipping_address'] = shipping_address.dict()

        # location
        shopify_location = self.shopify_client.find_location_by_id(
            shopify_order.location_id) or self.shopify_client.default_location

        if fuse5_location := self.find_location_by_name(shopify_location.name):
            params['sales_order_location'] = fuse5_location['location_name']
        else:
            params['sales_order_location'] = self.fuse5_default_location

        # tracking number
        if tracking_number := self.extract_tracking_number(shopify_order):
            params['tracking_number'] = tracking_number

        params["price_override"] = {
            "subtotal": shopify_order.subtotal_price,
            "tax": shopify_order.total_tax,
            "discount": float(shopify_order.total_discounts),
            "handling": 0.00,
            "shipping": shopify_order.total_shipping_price_set.shop_money.amount,
            "total": shopify_order.total_price
        }

        try:
            res = self.fuse5.create_sales_order(params)
        except Exception as e:
            logger.error("Error happened during order creating. %s", e)
            return None

        if 'sales_order_number' in res:
            logger.info("The Fuse5 order %s (%s) was created based on the Shopify order %s",
                        res['sales_order_number'],
                        res['sales_order_id'],
                        order_id_msg
                        )

            # for debug
            # logger.info(params)
            # pprint(res)
            # order = self.fuse5.get_sales_order(res['sales_order_number'])
            # pprint(order)

        else:
            logger.error('Unable to create an order %s for unknown reasons. Response data: %s', order_id_msg, res)

        return res

    def find_location_by_name(self, location_name: str) -> dict | None:
        return next((item for item in self.fuse5_locations if location_name in item['location_name']), None)

    @staticmethod
    def extract_tracking_number(shopify_order: Order) -> str | None:
        if shopify_order.fulfillments:
            return shopify_order.fulfillments[0].tracking_number

    def find_matched_products(self, shopify_order: Order, as_dict=False) -> list[Fuse5Product | dict]:
        fuse5_products = []
        for item in shopify_order.line_items:
            if variant := self.shopify_client.get_variant(item.variant_id):
                if product := self.products_finder.find_product_by_barcode_and_sku(variant.to_dict()):
                    f5_product = Fuse5Product(
                        line_code=product['line_code'],
                        product_number=product['sku'],
                        quantity=item.quantity,
                        price=item.price
                    )

                    if as_dict:
                        f5_product = f5_product.dict()

                    fuse5_products.append(f5_product)
            else:
                logger.warning("Can't find product variant ID=%s from the order ID=%s (%s)",
                               item.variant_id, shopify_order.id, shopify_order.order_number)

        return fuse5_products
