from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0138_benthiclit_include_bleaching_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="benthiclitobsmodel",
            name="bleaching_status",
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name="benthiclitobsmodel",
            name="include_bleaching",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="benthicpitobsmodel",
            name="bleaching_status",
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name="benthicpitobsmodel",
            name="include_bleaching",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="benthiclitsemodel",
            name="bleaching_sample_unit_count",
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="benthiclitsemodel",
            name="percent_bleached_hard_coral_avg",
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="benthiclitsemodel",
            name="percent_bleached_hard_coral_sd",
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="benthiclitsemodel",
            name="percent_bleached_soft_coral_avg",
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="benthiclitsemodel",
            name="percent_bleached_soft_coral_sd",
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="benthiclitsemodel",
            name="percent_bleached_total_coral_avg",
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="benthiclitsemodel",
            name="percent_bleached_total_coral_sd",
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="benthiclitsumodel",
            name="include_bleaching",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="benthiclitsumodel",
            name="percent_bleached_hard_coral",
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="benthiclitsumodel",
            name="percent_bleached_soft_coral",
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="benthiclitsumodel",
            name="percent_bleached_total_coral",
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="benthicpitsemodel",
            name="bleaching_sample_unit_count",
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="benthicpitsemodel",
            name="percent_bleached_hard_coral_avg",
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="benthicpitsemodel",
            name="percent_bleached_hard_coral_sd",
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="benthicpitsemodel",
            name="percent_bleached_soft_coral_avg",
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="benthicpitsemodel",
            name="percent_bleached_soft_coral_sd",
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="benthicpitsemodel",
            name="percent_bleached_total_coral_avg",
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="benthicpitsemodel",
            name="percent_bleached_total_coral_sd",
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="benthicpitsumodel",
            name="include_bleaching",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="benthicpitsumodel",
            name="percent_bleached_hard_coral",
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="benthicpitsumodel",
            name="percent_bleached_soft_coral",
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="benthicpitsumodel",
            name="percent_bleached_total_coral",
            field=models.JSONField(blank=True, null=True),
        ),
    ]
