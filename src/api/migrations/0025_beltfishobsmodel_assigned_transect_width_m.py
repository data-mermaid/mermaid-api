# Generated by Django 3.2.20 on 2023-10-16 20:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0024_auto_20230913_1858'),
    ]

    operations = [
        migrations.AddField(
            model_name='beltfishobsmodel',
            name='assigned_transect_width_m',
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
    ]
