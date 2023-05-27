# Generated by Django 4.2.1 on 2023-05-27 12:23

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='StockDataSource',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=30)),
                ('active', models.BooleanField()),
                ('processor', models.CharField(choices=[('FUSE_5', 'Fuse 5'), ('CUSTOM_CSV', 'Custom CSV')], max_length=20)),
                ('params', models.JSONField(blank=True, default=dict)),
            ],
        ),
    ]
