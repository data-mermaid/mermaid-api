# Generated by Django 2.2.12 on 2020-07-28 21:25

from django.db import migrations

from ..models.view_models import model_view_migrations


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0002_auto_20200728_1701'),
    ]

    operations = [
        migrations.RunSQL(model_view_migrations.reverse_sql(), model_view_migrations.forward_sql()),
    ]
