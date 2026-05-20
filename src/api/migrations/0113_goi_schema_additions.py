import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0112_bump_proposed_attribute_revisions"),
    ]

    operations = [
        # 1. Add nullable group_of_interest FK on InvertGenus.
        #    Populated in 0114; made non-nullable in 0115.
        migrations.AddField(
            model_name="invertgenus",
            name="group_of_interest",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                to="api.invertgroupofinterest",
            ),
        ),
        # 2. Remove unique_invertorder_name_class_goi before the FK change and
        #    InvertOrder de-duplication in 0114.
        migrations.RemoveConstraint(
            model_name="invertorder",
            name="unique_invertorder_name_class_goi",
        ),
        # 3. Add nullable invert_class FK on InvertOrder.
        #    Populated in 0114; made non-nullable in 0115.
        migrations.AddField(
            model_name="invertorder",
            name="invert_class",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="orders",
                to="api.invertclass",
            ),
        ),
        # 4. Remove unique_invertfamily_name_order before InvertFamily de-duplication
        #    in 0114 (two Muricidae rows temporarily share the same (name, order)
        #    after InvertOrder de-duplication merges them under one parent).
        migrations.RemoveConstraint(
            model_name="invertfamily",
            name="unique_invertfamily_name_order",
        ),
        # 5. Add nullable invertattribute_ptr on InvertGroupOfInterest to begin MTI
        #    promotion. Populated in 0114; promoted to PK in 0115.
        migrations.AddField(
            model_name="invertgroupofinterest",
            name="invertattribute_ptr",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="api.invertattribute",
            ),
        ),
    ]
