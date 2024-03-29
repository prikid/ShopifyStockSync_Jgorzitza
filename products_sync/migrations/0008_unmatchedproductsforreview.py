# Generated by Django 4.2.2 on 2023-08-30 14:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products_sync', '0007_fuse5products_products_sy_sku_45f168_idx'),
    ]

    operations = [
        migrations.CreateModel(
            name='UnmatchedProductsForReview',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('shopify_product_id', models.PositiveBigIntegerField()),
                ('shopify_variant_id', models.PositiveBigIntegerField()),
                ('shopify_sku', models.CharField(max_length=30, null=True)),
                ('shopify_barcode', models.CharField(max_length=20, null=True)),
                ('shopify_variant_title', models.CharField()),
                ('possible_fuse5_products', models.JSONField()),
            ],
            options={
                'indexes': [models.Index(fields=['shopify_sku'], name='products_sy_shopify_4a3d59_idx'), models.Index(fields=['shopify_barcode'], name='products_sy_shopify_94a03b_idx')],
                'unique_together': {('shopify_product_id', 'shopify_variant_id')},
            },
        ),
    ]
