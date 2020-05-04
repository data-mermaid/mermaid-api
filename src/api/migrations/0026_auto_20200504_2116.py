# Generated by Django 2.2.9 on 2020-05-04 21:16

from django.db import migrations
from ..models.view_models import BeltFishSEView

drop_fb_se_view = "DROP VIEW IF EXISTS public.vw_beltfish_se;"


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0025_auto_20200430_1636'),
    ]

    operations = [
        migrations.RunSQL(drop_fb_se_view, BeltFishSEView.sql),
        migrations.RunSQL(BeltFishSEView.sql, drop_fb_se_view),
    ]
