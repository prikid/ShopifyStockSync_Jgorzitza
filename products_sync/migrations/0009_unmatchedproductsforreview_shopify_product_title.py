# Generated by Django 4.2.2 on 2023-09-28 18:36

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products_sync', '0008_unmatchedproductsforreview'),
    ]

    operations = [
        migrations.AddField(
            model_name='unmatchedproductsforreview',
            name='shopify_product_title',
            field=models.CharField(null=True),
        ),
    ]
