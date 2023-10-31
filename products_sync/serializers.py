import html

from rest_framework import serializers

from app import settings
from .models import StockDataSource, ProductsUpdateLog, UnmatchedProductsForReview, HiddenProductsFromUnmatchedReview


class StockDataSourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockDataSource
        fields = ['id', 'name', 'active', 'processor', 'params']
        read_only_fields = ['id']


class ProductsUpdateLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductsUpdateLog
        fields = ['gid', 'source', 'time', 'sku', 'product_id', 'variant_id', 'barcode', 'changes']
        read_only_fields = fields


class UnmatchedProductsForReviewSerializer(serializers.ModelSerializer):
    possible_fuse5_products = serializers.SerializerMethodField()
    product_url = serializers.SerializerMethodField()
    variant_url = serializers.SerializerMethodField()
    is_hidden = serializers.SerializerMethodField()

    class Meta:
        model = UnmatchedProductsForReview
        fields = ['id', 'shopify_product_id', 'shopify_product_title', 'shopify_variant_id', 'shopify_sku',
                  'shopify_barcode',
                  'shopify_variant_title',
                  'possible_fuse5_products', 'product_url', 'variant_url', 'is_hidden']
        read_only_fields = fields

    def get_possible_fuse5_products(self, obj):
        products = []
        for p in obj.possible_fuse5_products:
            p['product_name'] = html.unescape(p['product_name'] or '')
            products.append(p)

        return products

    def get_product_url(self, obj):
        return f"https://admin.shopify.com/store/{settings.SHOPIFY_SHOP_NAME}/products/{obj.shopify_product_id}"

    def get_variant_url(self, obj):
        return self.get_product_url(obj) + f"/variants/{obj.shopify_variant_id}"

    def get_is_hidden(self, obj):
        return obj.is_hidden()


class HiddenProductsFromUnmatchedReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = HiddenProductsFromUnmatchedReview
        fields = ['id', 'shopify_product_id', 'shopify_variant_id']
