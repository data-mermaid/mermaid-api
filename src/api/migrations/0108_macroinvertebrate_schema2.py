import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0107_macroinvertebrate_data"),
    ]

    operations = [
        # 1. Remove harvest_type FK from InvertSpecies.
        migrations.RemoveField(
            model_name="invertspecies",
            name="harvest_type",
        ),
        # 2. Make InvertBeltTransect.size_bin nullable.
        migrations.AlterField(
            model_name="invertbelttransect",
            name="size_bin",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                to="api.invertsizebin",
                verbose_name="size bin (cm)",
            ),
        ),
        # 3. Create InvertClassGroupOfInterest as an InvertAttribute MTI child.
        migrations.CreateModel(
            name="InvertClassGroupOfInterest",
            fields=[
                (
                    "invertattribute_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="api.invertattribute",
                    ),
                ),
                (
                    "invert_class",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="class_gois",
                        to="api.invertclass",
                    ),
                ),
                (
                    "group_of_interest",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="class_gois",
                        to="api.invertgroupofinterest",
                    ),
                ),
            ],
            options={
                "verbose_name": "macroinvertebrate class / group of interest",
                "verbose_name_plural": "macroinvertebrate class / groups of interest",
                "db_table": "invert_class_goi",
                "ordering": ("invert_class__name", "group_of_interest__name"),
            },
            bases=("api.invertattribute",),
        ),
        migrations.AddConstraint(
            model_name="invertclassgroupofinterest",
            constraint=models.UniqueConstraint(
                fields=["invert_class", "group_of_interest"],
                name="unique_invert_class_goi",
            ),
        ),
        # 4. Drop the old InvertOrder unique constraint before adding the nullable FK
        #    (a new constraint referencing class_goi will be added in 0110 after the
        #    data migration populates the field).
        migrations.RemoveConstraint(
            model_name="invertorder",
            name="unique_invertorder_name_invert_class",
        ),
        # 5. Add nullable class_goi FK on InvertOrder.
        migrations.AddField(
            model_name="invertorder",
            name="class_goi",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="orders",
                to="api.invertclassgroupofinterest",
            ),
        ),
    ]
