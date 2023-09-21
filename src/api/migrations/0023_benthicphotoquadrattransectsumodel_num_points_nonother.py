# Generated by Django 3.2.20 on 2023-09-12 17:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0022_auto_20230803_1702'),
    ]

    operations = [
        migrations.AddField(
            model_name='benthicphotoquadrattransectsumodel',
            name='num_points_nonother',
            field=models.PositiveSmallIntegerField(default=0, verbose_name="number of non-'Other' points for all observations in all quadrats for the transect"),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='benthicphotoquadrattransectsemodel',
            name='num_points_nonother',
            field=models.PositiveSmallIntegerField(default=0,
                                                   verbose_name="number of non-'Other' points for all observations in all transects for the sample event"),
            preserve_default=False,
        ),
    ]
