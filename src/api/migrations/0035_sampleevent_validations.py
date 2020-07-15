# Generated by Django 2.2.12 on 2020-07-14 21:13

import django.contrib.postgres.fields.jsonb
from django.db import migrations
import rest_framework.utils.encoders


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0034_merge_20200714_2103'),
    ]

    operations = [
        migrations.AddField(
            model_name='sampleevent',
            name='validations',
            field=django.contrib.postgres.fields.jsonb.JSONField(blank=True, encoder=rest_framework.utils.encoders.JSONEncoder, null=True),
        ),
    ]
