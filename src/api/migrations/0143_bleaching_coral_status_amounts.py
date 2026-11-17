# M2136: per-status coral amounts (bleaching_{hard,soft}_coral objects) replace the coral amount totals.
# Summary tables are caches rebuilt by update_cache, so changed columns are dropped and re-added.

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0142_merge_20261117_1912"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="benthiclitsumodel",
            name="bleaching_hard_coral_length",
        ),
        migrations.AddField(
            model_name="benthiclitsumodel",
            name="bleaching_hard_coral",
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.RemoveField(
            model_name="benthiclitsumodel",
            name="bleaching_soft_coral_length",
        ),
        migrations.AddField(
            model_name="benthiclitsumodel",
            name="bleaching_soft_coral",
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.RemoveField(
            model_name="benthiclitsemodel",
            name="bleaching_hard_coral_length",
        ),
        migrations.AddField(
            model_name="benthiclitsemodel",
            name="bleaching_hard_coral",
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.RemoveField(
            model_name="benthiclitsemodel",
            name="bleaching_soft_coral_length",
        ),
        migrations.AddField(
            model_name="benthiclitsemodel",
            name="bleaching_soft_coral",
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.RemoveField(
            model_name="benthicpitsumodel",
            name="bleaching_hard_coral_points",
        ),
        migrations.AddField(
            model_name="benthicpitsumodel",
            name="bleaching_hard_coral",
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.RemoveField(
            model_name="benthicpitsumodel",
            name="bleaching_soft_coral_points",
        ),
        migrations.AddField(
            model_name="benthicpitsumodel",
            name="bleaching_soft_coral",
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.RemoveField(
            model_name="benthicpitsemodel",
            name="bleaching_hard_coral_points",
        ),
        migrations.AddField(
            model_name="benthicpitsemodel",
            name="bleaching_hard_coral",
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.RemoveField(
            model_name="benthicpitsemodel",
            name="bleaching_soft_coral_points",
        ),
        migrations.AddField(
            model_name="benthicpitsemodel",
            name="bleaching_soft_coral",
            field=models.JSONField(blank=True, null=True),
        ),
    ]
