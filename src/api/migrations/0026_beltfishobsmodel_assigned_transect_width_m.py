# Generated by Django 3.2.20 on 2023-10-16 20:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0025_auto_20231012_1308'),
    ]

    operations = [
        migrations.AddField(
            model_name='beltfishobsmodel',
            name='assigned_transect_width_m',
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
    ]