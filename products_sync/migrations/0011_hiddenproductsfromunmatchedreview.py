# Generated by Django 4.2.2 on 2023-10-24 16:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products_sync', '0010_customcsv_remove_customcsvdata_created_at_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='HiddenProductsFromUnmatchedReview',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('shopify_product_id', models.PositiveBigIntegerField()),
                ('shopify_variant_id', models.PositiveBigIntegerField()),
            ],
            options={
                'unique_together': {('shopify_product_id', 'shopify_variant_id')},
            },
        ),
    ]
