# Generated by Django 3.2.20 on 2023-09-13 18:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0023_benthicphotoquadrattransectsumodel_num_points_nonother'),
    ]

    operations = [
        migrations.AddField(
            model_name='beltfishsemodel',
            name='depth_sd',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=4, null=True, verbose_name='depth standard deviation (m)'),
        ),
        migrations.AddField(
            model_name='benthiclitsemodel',
            name='depth_sd',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=4, null=True, verbose_name='depth standard deviation (m)'),
        ),
        migrations.AddField(
            model_name='benthicphotoquadrattransectsemodel',
            name='depth_sd',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=4, null=True, verbose_name='depth standard deviation (m)'),
        ),
        migrations.AddField(
            model_name='benthicpitsemodel',
            name='depth_sd',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=4, null=True, verbose_name='depth standard deviation (m)'),
        ),
        migrations.AddField(
            model_name='bleachingqcsemodel',
            name='depth_sd',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=4, null=True, verbose_name='depth standard deviation (m)'),
        ),
        migrations.AddField(
            model_name='habitatcomplexitysemodel',
            name='depth_sd',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=4, null=True, verbose_name='depth standard deviation (m)'),
        ),
        migrations.AlterField(
            model_name='beltfishsemodel',
            name='depth_avg',
            field=models.DecimalField(decimal_places=2, max_digits=4, verbose_name='depth mean (m)'),
        ),
        migrations.AlterField(
            model_name='benthiclitsemodel',
            name='depth_avg',
            field=models.DecimalField(decimal_places=2, max_digits=4, verbose_name='depth mean (m)'),
        ),
        migrations.AlterField(
            model_name='benthicphotoquadrattransectsemodel',
            name='depth_avg',
            field=models.DecimalField(decimal_places=2, max_digits=4, verbose_name='depth mean (m)'),
        ),
        migrations.AlterField(
            model_name='benthicpitsemodel',
            name='depth_avg',
            field=models.DecimalField(decimal_places=2, max_digits=4, verbose_name='depth mean (m)'),
        ),
        migrations.AlterField(
            model_name='bleachingqcsemodel',
            name='depth_avg',
            field=models.DecimalField(decimal_places=2, max_digits=4, verbose_name='depth mean (m)'),
        ),
        migrations.AlterField(
            model_name='habitatcomplexitysemodel',
            name='depth_avg',
            field=models.DecimalField(decimal_places=2, max_digits=4, verbose_name='depth mean (m)'),
        ),
        migrations.AddField(
            model_name='beltfishsemodel',
            name='biomass_kgha_sd',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True,
                                      verbose_name='biomass standard deviation (kg/ha)'),
        ),
        migrations.AlterField(
            model_name='beltfishsemodel',
            name='biomass_kgha_avg',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True,
                                      verbose_name='biomass mean (kg/ha)'),
        ),
        migrations.AddField(
            model_name='beltfishsemodel',
            name='biomass_kgha_by_fish_family_sd',
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='beltfishsemodel',
            name='biomass_kgha_by_trophic_group_sd',
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='bleachingqcsemodel',
            name='count_genera_sd',
            field=models.DecimalField(blank=True, decimal_places=1, max_digits=4, null=True),
        ),
        migrations.AddField(
            model_name='bleachingqcsemodel',
            name='count_total_sd',
            field=models.DecimalField(blank=True, decimal_places=1, max_digits=5, null=True),
        ),
        migrations.AddField(
            model_name='bleachingqcsemodel',
            name='percent_algae_avg_sd',
            field=models.DecimalField(blank=True, decimal_places=1, max_digits=4, null=True),
        ),
        migrations.AddField(
            model_name='bleachingqcsemodel',
            name='percent_bleached_sd',
            field=models.DecimalField(blank=True, decimal_places=1, max_digits=4, null=True),
        ),
        migrations.AddField(
            model_name='bleachingqcsemodel',
            name='percent_hard_avg_sd',
            field=models.DecimalField(blank=True, decimal_places=1, max_digits=4, null=True),
        ),
        migrations.AddField(
            model_name='bleachingqcsemodel',
            name='percent_normal_sd',
            field=models.DecimalField(blank=True, decimal_places=1, max_digits=4, null=True),
        ),
        migrations.AddField(
            model_name='bleachingqcsemodel',
            name='percent_pale_sd',
            field=models.DecimalField(blank=True, decimal_places=1, max_digits=4, null=True),
        ),
        migrations.AddField(
            model_name='bleachingqcsemodel',
            name='percent_soft_avg_sd',
            field=models.DecimalField(blank=True, decimal_places=1, max_digits=4, null=True),
        ),
        migrations.AddField(
            model_name='habitatcomplexitysemodel',
            name='score_avg_sd',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=3, null=True),
        ),
        migrations.AddField(
            model_name='benthiclitsemodel',
            name='percent_cover_by_benthic_category_sd',
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='benthicphotoquadrattransectsemodel',
            name='percent_cover_by_benthic_category_sd',
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='benthicpitsemodel',
            name='percent_cover_by_benthic_category_sd',
            field=models.JSONField(blank=True, null=True),
        ),
    ]
