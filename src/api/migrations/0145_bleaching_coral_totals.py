# M2136: the per-status bleaching_{hard,soft}_coral objects are replaced by one total per coral type,
# bleaching_{hard,soft}_coral_points (PIT) / _length (LIT, cm).
# Summary tables are caches rebuilt by update_cache, so changed columns are dropped and re-added.

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0144_bleaching_status_choice_names"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="benthiclitsumodel",
            name="bleaching_hard_coral",
        ),
        migrations.AddField(
            model_name="benthiclitsumodel",
            name="bleaching_hard_coral_length",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.RemoveField(
            model_name="benthiclitsumodel",
            name="bleaching_soft_coral",
        ),
        migrations.AddField(
            model_name="benthiclitsumodel",
            name="bleaching_soft_coral_length",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.RemoveField(
            model_name="benthiclitsemodel",
            name="bleaching_hard_coral",
        ),
        migrations.AddField(
            model_name="benthiclitsemodel",
            name="bleaching_hard_coral_length",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.RemoveField(
            model_name="benthiclitsemodel",
            name="bleaching_soft_coral",
        ),
        migrations.AddField(
            model_name="benthiclitsemodel",
            name="bleaching_soft_coral_length",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.RemoveField(
            model_name="benthicpitsumodel",
            name="bleaching_hard_coral",
        ),
        migrations.AddField(
            model_name="benthicpitsumodel",
            name="bleaching_hard_coral_points",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.RemoveField(
            model_name="benthicpitsumodel",
            name="bleaching_soft_coral",
        ),
        migrations.AddField(
            model_name="benthicpitsumodel",
            name="bleaching_soft_coral_points",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.RemoveField(
            model_name="benthicpitsemodel",
            name="bleaching_hard_coral",
        ),
        migrations.AddField(
            model_name="benthicpitsemodel",
            name="bleaching_hard_coral_points",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.RemoveField(
            model_name="benthicpitsemodel",
            name="bleaching_soft_coral",
        ),
        migrations.AddField(
            model_name="benthicpitsemodel",
            name="bleaching_soft_coral_points",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
    ]
