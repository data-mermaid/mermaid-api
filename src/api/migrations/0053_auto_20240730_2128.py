# Generated by Django 3.2.20 on 2024-07-30 21:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0052_merge_0050_auto_20240724_2150_0051_auto_20240725_2108'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='point',
            name='point_number',
        ),
        migrations.AlterField(
            model_name='classifier',
            name='version',
            field=models.CharField(help_text='Classifier version (pattern: v[Version Number])', max_length=11),
        ),
    ]
