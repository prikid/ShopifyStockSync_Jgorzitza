# Generated by Django 4.2.2 on 2023-08-30 09:26

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products_sync', '0006_fuse5products'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='fuse5products',
            index=models.Index(fields=['sku'], name='products_sy_sku_45f168_idx'),
        ),
    ]
