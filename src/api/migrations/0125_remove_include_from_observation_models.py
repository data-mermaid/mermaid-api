from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0124_mv_invert_attributes_goi_family_order_class"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="obsbeltinvert",
            name="include",
        ),
        migrations.RemoveField(
            model_name="obsbeltfish",
            name="include",
        ),
        migrations.RemoveField(
            model_name="obsbenthiclit",
            name="include",
        ),
        migrations.RemoveField(
            model_name="obsbenthicpit",
            name="include",
        ),
        migrations.RemoveField(
            model_name="obshabitatcomplexity",
            name="include",
        ),
        migrations.RemoveField(
            model_name="beltinvertobsmodel",
            name="include",
        ),
        migrations.RemoveField(
            model_name="beltinvertobssqlmodel",
            name="include",
        ),
    ]
