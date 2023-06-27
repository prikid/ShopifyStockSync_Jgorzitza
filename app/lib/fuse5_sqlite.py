import logging
import sqlite3

import pandas as pd


class Fuse5Sqlite:
    def __init__(self, df: pd.DataFrame, logger: logging.Logger = None):
        self.logger = logger or logging.getLogger(__name__)

        self.logger.info('Indexing suppliers data for search...')
        self.sqlite_conn = sqlite3.connect(':memory:')
        df.to_sql('supplier_products', self.sqlite_conn)

        self.sqlite_conn.execute("CREATE INDEX barcode_idx ON supplier_products (barcode)")

    def __del__(self):
        self.sqlite_conn.close()

    def find_product_by_barcode_and_sku(self, shopify_variant_data: dict) -> dict | None:
        def log_no_sku_warning(products: list):
            if len(products) > 1:
                msg_tmpl = "A few products with the barcode %s have been found in the supplier's data, but no one " \
                           "matched the SKU %s. Will use the first one.\n Shopify product:%s \nSupplier's products:"
            else:
                msg_tmpl = "A product with the barcode %s has been found in the supplier's data, but the SKU %s do " \
                           "not match. \n\tShopify product:%s \n\tSupplier's product:"

            shopify_variant_data_str = "\n\t\tproduct_id={product_id}; variant_id={id}; sku={sku}; barcode={barcode} ".format(
                **shopify_variant_data)

            msg = msg_tmpl % (barcode, sku, shopify_variant_data_str)

            for product in products:
                msg += "\n\t\tbarcode={barcode}; sku={sku}; name={product_name}".format(**product)

            self.logger.warning(msg)

        barcode, sku = shopify_variant_data['barcode'], shopify_variant_data['sku']

        if barcode is None:
            return None

        # create variants of the barcode of different length by filling leading zeros
        barcodes = [barcode.zfill(i) for i in range(len(barcode), 15)]

        placeholders = ','.join(['?'] * len(barcodes))
        query = f"SELECT * FROM supplier_products WHERE barcode IN ({placeholders})"
        supplier_products = pd.read_sql_query(query, self.sqlite_conn, params=barcodes)

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
