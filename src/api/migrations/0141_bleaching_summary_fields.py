# M2136: pooled SE bleaching percents, coral amounts and per-status SU amounts; integer obs bleaching status.
# Summary tables are caches rebuilt by update_cache, so changed columns are dropped and re-added.

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0140_benthiclit_include_bleaching_and_more"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="benthiclitobsmodel",
            name="bleaching_status",
        ),
        migrations.AddField(
            model_name="benthiclitobsmodel",
            name="bleaching_status",
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="benthiclitobsmodel",
            name="bleaching_status_name",
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.RemoveField(
            model_name="benthiclitsumodel",
            name="percent_bleached_total_coral",
        ),
        migrations.AddField(
            model_name="benthiclitsumodel",
            name="bleaching_hard_coral_length",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="benthiclitsumodel",
            name="bleaching_soft_coral_length",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="benthiclitsumodel",
            name="bleaching_status_amounts",
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.RemoveField(
            model_name="benthiclitsemodel",
            name="percent_bleached_hard_coral_avg",
        ),
        migrations.RemoveField(
            model_name="benthiclitsemodel",
            name="percent_bleached_soft_coral_avg",
        ),
        migrations.RemoveField(
            model_name="benthiclitsemodel",
            name="percent_bleached_total_coral_avg",
        ),
        migrations.AddField(
            model_name="benthiclitsemodel",
            name="bleaching_hard_coral_sample_unit_count",
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="benthiclitsemodel",
            name="bleaching_soft_coral_sample_unit_count",
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="benthiclitsemodel",
            name="bleaching_hard_coral_length",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="benthiclitsemodel",
            name="bleaching_soft_coral_length",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="benthiclitsemodel",
            name="percent_bleached_hard_coral",
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="benthiclitsemodel",
            name="percent_bleached_soft_coral",
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.RemoveField(
            model_name="benthicpitobsmodel",
            name="bleaching_status",
        ),
        migrations.AddField(
            model_name="benthicpitobsmodel",
            name="bleaching_status",
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="benthicpitobsmodel",
            name="bleaching_status_name",
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.RemoveField(
            model_name="benthicpitsumodel",
            name="percent_bleached_total_coral",
        ),
        migrations.AddField(
            model_name="benthicpitsumodel",
            name="bleaching_hard_coral_points",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="benthicpitsumodel",
            name="bleaching_soft_coral_points",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="benthicpitsumodel",
            name="bleaching_status_amounts",
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.RemoveField(
            model_name="benthicpitsemodel",
            name="percent_bleached_hard_coral_avg",
        ),
        migrations.RemoveField(
            model_name="benthicpitsemodel",
            name="percent_bleached_soft_coral_avg",
        ),
        migrations.RemoveField(
            model_name="benthicpitsemodel",
            name="percent_bleached_total_coral_avg",
        ),
        migrations.AddField(
            model_name="benthicpitsemodel",
            name="bleaching_hard_coral_sample_unit_count",
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="benthicpitsemodel",
            name="bleaching_soft_coral_sample_unit_count",
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="benthicpitsemodel",
            name="bleaching_hard_coral_points",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="benthicpitsemodel",
            name="bleaching_soft_coral_points",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="benthicpitsemodel",
            name="percent_bleached_hard_coral",
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="benthicpitsemodel",
            name="percent_bleached_soft_coral",
            field=models.JSONField(blank=True, null=True),
        ),
    ]
