# Generated by Django 2.2.12 on 2021-07-05 19:33

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0005_auto_20210512_2212'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='obsbeltfish',
            name='size_bin',
        ),
    ]
