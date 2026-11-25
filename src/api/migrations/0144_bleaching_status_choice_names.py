# M2136: bleaching status choice names use underscores (e.g. "fully_bleached"). State-only change.

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0143_bleaching_coral_status_amounts"),
    ]

    operations = [
        migrations.AlterField(
            model_name="obsbenthiclit",
            name="bleaching_status",
            field=models.PositiveSmallIntegerField(
                blank=True,
                choices=[
                    (0, "normal"),
                    (1, "pale"),
                    (2, "partially_bleached"),
                    (3, "fully_bleached"),
                    (4, "recent_bleaching_mortality"),
                ],
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="obsbenthicpit",
            name="bleaching_status",
            field=models.PositiveSmallIntegerField(
                blank=True,
                choices=[
                    (0, "normal"),
                    (1, "pale"),
                    (2, "partially_bleached"),
                    (3, "fully_bleached"),
                    (4, "recent_bleaching_mortality"),
                ],
                null=True,
            ),
        ),
    ]
