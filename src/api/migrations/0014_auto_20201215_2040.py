# Generated by Django 2.2.12 on 2020-12-15 20:40

from django.db import migrations
from ..models.view_models import (
    model_view_migrations,
)


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0013_auto_20201215_1812'),
    ]

    operations = [
        migrations.RunSQL(
            model_view_migrations.reverse_sql(), model_view_migrations.forward_sql()
        ),
        migrations.RunSQL(
            model_view_migrations.forward_sql(), model_view_migrations.reverse_sql()
        ),
    ]
