# Generated by Django 2.2.12 on 2020-07-15 17:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0033_auto_20200717_1528'),
    ]

    operations = [
        migrations.AddField(
            model_name='management',
            name='access_restriction',
            field=models.BooleanField(default=False, verbose_name='access restriction'),
        ),
    ]
