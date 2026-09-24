from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0122_mv_invert_attributes"),
    ]

    operations = [
        migrations.RenameField(
            model_name="beltinvertobsmodel",
            old_name="invert_attribute_name",
            new_name="invert_taxon",
        ),
        migrations.AddField(
            model_name="beltinvertobsmodel",
            name="invert_group_of_interest",
            field=models.CharField(blank=True, max_length=200, null=True),
        ),
        migrations.AddField(
            model_name="beltinvertobsmodel",
            name="invert_class",
            field=models.CharField(blank=True, max_length=200, null=True),
        ),
        migrations.AddField(
            model_name="beltinvertobsmodel",
            name="invert_order",
            field=models.CharField(blank=True, max_length=200, null=True),
        ),
        migrations.AddField(
            model_name="beltinvertobsmodel",
            name="invert_family",
            field=models.CharField(blank=True, max_length=200, null=True),
        ),
        migrations.AddField(
            model_name="beltinvertobsmodel",
            name="invert_genus",
            field=models.CharField(blank=True, max_length=200, null=True),
        ),
        migrations.AddField(
            model_name="beltinvertobsmodel",
            name="invert_species",
            field=models.CharField(blank=True, max_length=200, null=True),
        ),
        migrations.AddField(
            model_name="beltinvertobsmodel",
            name="density_indha",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=11, null=True),
        ),
        migrations.AddField(
            model_name="beltinvertobsmodel",
            name="observation_notes",
            field=models.TextField(blank=True, null=True),
        ),
    ]
