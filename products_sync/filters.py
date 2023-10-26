from django.db.models import OuterRef, Subquery
from rest_framework import filters

from products_sync.models import HiddenProductsFromUnmatchedReview


class ShowHiddenFilterBackend(filters.BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        show_hidden = request.query_params.get('show_hidden')

        if show_hidden and show_hidden.lower() == 'false':
            hidden_items_subquery = HiddenProductsFromUnmatchedReview.objects.filter(
                shopify_product_id=OuterRef('shopify_product_id'),
                shopify_variant_id=OuterRef('shopify_variant_id')
            ).values('shopify_product_id', 'shopify_variant_id')

            # Exclude UnmatchedProductsForReview items with matching hidden items
            queryset = queryset.exclude(
                shopify_product_id__in=Subquery(hidden_items_subquery.values('shopify_product_id')),
                shopify_variant_id__in=Subquery(hidden_items_subquery.values('shopify_variant_id'))
            )

        # By default, do not filter
        return queryset
