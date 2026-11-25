# M2136: sample event standard deviation of the SUs' percent bleached (all non-normal statuses),
# per coral type.

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0145_bleaching_coral_totals"),
    ]

    operations = [
        migrations.AddField(
            model_name="benthiclitsemodel",
            name="percent_bleached_hard_coral_sd",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True),
        ),
        migrations.AddField(
            model_name="benthiclitsemodel",
            name="percent_bleached_soft_coral_sd",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True),
        ),
        migrations.AddField(
            model_name="benthicpitsemodel",
            name="percent_bleached_hard_coral_sd",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True),
        ),
        migrations.AddField(
            model_name="benthicpitsemodel",
            name="percent_bleached_soft_coral_sd",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True),
        ),
    ]
