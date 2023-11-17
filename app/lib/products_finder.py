import html
import logging
import re
import sqlite3
from abc import abstractmethod

import pandas as pd
from django.db.models import Model, QuerySet


class BaseProductsFinder:
    table_name: str

    def __init__(self, logger: logging.Logger = None, default_location_name: str = None):
        self.default_location_name = default_location_name
        self.logger = logger or logging.getLogger(__name__)

    def fill_default_location(self, df: pd.DataFrame):
        if self.default_location_name is not None:
            if 'location_name' not in df.columns:
                df['location_name'] = self.default_location_name
            else:
                df['location_name'].fillna(self.default_location_name, inplace=True)

        return df

    @abstractmethod
    def find_by_barcodes(self, barcodes: list) -> pd.DataFrame:
        ...

    @abstractmethod
    def find_by_sku(self, sku: str) -> pd.DataFrame:
        ...

    def find_products_by_sku(self, shopify_variant_data: dict) -> list[dict] | None:
        sku = shopify_variant_data['sku']
        supplier_products = self.find_by_sku(sku)

        if supplier_products.empty:
            return None

        return supplier_products.to_dict(orient='records')

    def find_product_by_barcode_and_sku(self, shopify_variant_data: dict) -> dict | None:
        def log_no_sku_warning(_supplier_products: list[dict]):
            if len(_supplier_products) > 1:
                msg_tmpl = "A few products with the barcode %s have been found in the supplier's data, but no one " \
                           "matched the SKU %s. Will use the first one.\n Shopify product:%s \nSupplier's products:"
            else:
                msg_tmpl = "A product with the barcode %s has been found in the supplier's data, but the SKU %s do " \
                           "not match. \n\tShopify product:%s \n\tSupplier's product:"

            shopify_variant_data_str = "\n\t\tproduct_id={product_id}; variant_id={id}; sku={sku}; barcode={barcode} ".format(
                **shopify_variant_data)

            msg = msg_tmpl % (barcode, sku, shopify_variant_data_str)

            for product in _supplier_products:
                msg += "\n\t\tbarcode={barcode}; sku={sku}".format(**product)
                if 'product_name' in product:
                    msg += "; name=%s" % html.unescape(product['product_name'] or '')

            self.logger.warning(msg)

        barcode, sku = shopify_variant_data['barcode'], shopify_variant_data['sku']

        if barcode is None:
            return None

        # create variants of the barcode of different length by filling leading zeros
        barcodes = [barcode.zfill(i) for i in range(len(barcode), 15)]
        supplier_products = self.find_by_barcodes(barcodes)

        if supplier_products.empty:
            return None

        found_product: pd.Series = supplier_products.iloc[0]

        if sku is not None:
            narrowed_by_sku = supplier_products[supplier_products['sku'] == sku]
            if narrowed_by_sku.empty:
                log_no_sku_warning(supplier_products.to_dict("records"))
            else:
                found_product = narrowed_by_sku.iloc[0]

        return found_product.to_dict()


class ProductsFinder(BaseProductsFinder):

    def __init__(self, supplier_products: QuerySet | Model, logger: logging.Logger = None,
                 default_location_name: str = None):
        super().__init__(logger, default_location_name)

        self.supplier_products = supplier_products if isinstance(supplier_products,
                                                                 QuerySet) else supplier_products
        self.table_name = self.supplier_products.model._meta.db_table

    def find_by_barcodes(self, barcodes: list) -> pd.DataFrame:
        filtered_records = self.supplier_products.filter(barcode__in=barcodes)
        return self._get_found_df(filtered_records)

    def find_by_sku(self, sku: str) -> pd.DataFrame:
        # filtered_records = self.supplier_products.filter(sku__iexact=sku)

        regex_pattern = re.sub(r'(.)', '\g<1>[-_ ]*', re.sub(r"[-_ ]", '', sku))
        regex_pattern = f"^{regex_pattern}$"
        filtered_records = self.supplier_products.filter(sku__iregex=regex_pattern)

        return self._get_found_df(filtered_records)

    def _get_found_df(self, filtered_records) -> pd.DataFrame:
        if filtered_records.exists():
            df = pd.DataFrame.from_records(filtered_records.values())
        else:
            field_names = [field.name for field in self.supplier_products.model._meta.get_fields()]
            df = pd.DataFrame(columns=field_names)

        df = self.fill_default_location(df)

        return df


class SqliteProductsFinder(BaseProductsFinder):
    def __init__(self, df: pd.DataFrame, logger: logging.Logger = None, default_location_name: str = None):
        super().__init__(logger, default_location_name)
        self.table_name = 'supplier_products'

        self.logger.info('Indexing suppliers data for search...')
        self.sqlite_conn = sqlite3.connect(':memory:')
        df.to_sql('supplier_products', self.sqlite_conn)

        self.sqlite_conn.execute("CREATE INDEX barcode_idx ON supplier_products (barcode)")

    def __del__(self):
        self.sqlite_conn.close()

    def find_by_barcodes(self, barcodes: list) -> pd.DataFrame:
        placeholders = ','.join(['?'] * len(barcodes))
        query = f"SELECT * FROM {self.table_name} WHERE barcode IN ({placeholders})"

        df = pd.read_sql_query(query, self.sqlite_conn, params=barcodes)

        df = self.fill_default_location(df)

        return df

    @abstractmethod
    def find_by_sku(self, sku: str) -> pd.DataFrame:
        raise NotImplementedError
