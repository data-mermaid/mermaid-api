# Generated by Django 2.2.24 on 2021-11-08 13:30

import api.models.mermaid
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0011_auto_20210923_0946'),
    ]

    operations = [
        migrations.AlterField(
            model_name='sampleevent',
            name='management',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='api.Management'),
        ),
        migrations.AlterField(
            model_name='sampleevent',
            name='sample_date',
            field=models.DateField(default=api.models.mermaid.default_date),
        ),
        migrations.AlterField(
            model_name='sampleevent',
            name='site',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='sample_events', to='api.Site'),
        ),
    ]