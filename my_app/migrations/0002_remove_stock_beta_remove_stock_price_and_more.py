# Generated by Django 5.1.3 on 2024-12-17 02:08

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('my_app', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='stock',
            name='beta',
        ),
        migrations.RemoveField(
            model_name='stock',
            name='price',
        ),
        migrations.RemoveField(
            model_name='stock',
            name='volatility',
        ),
    ]
