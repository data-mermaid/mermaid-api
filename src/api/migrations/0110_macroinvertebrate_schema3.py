import django.db.models.deletion
from django.db import migrations, models


def delete_invert_phyla(apps, schema_editor):
    """Delete all InvertPhylum rows via their InvertAttribute parent.

    Deleting InvertAttribute rows cascades to InvertPhylum via the MTI parent link,
    leaving the invert_phylum table empty so DeleteModel can drop it cleanly.
    The phylum FK on InvertClass has already been removed above this RunPython call,
    so there are no remaining FK constraints blocking deletion.
    """
    InvertPhylum = apps.get_model("api", "InvertPhylum")
    InvertAttribute = apps.get_model("api", "InvertAttribute")
    phylum_attr_ids = list(InvertPhylum.objects.values_list("invertattribute_ptr_id", flat=True))
    InvertAttribute.objects.filter(pk__in=phylum_attr_ids).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0109_macroinvertebrate_data2"),
    ]

    operations = [
        # 1. Make InvertOrder.class_goi non-nullable now that all rows are populated.
        migrations.AlterField(
            model_name="invertorder",
            name="class_goi",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="orders",
                to="api.invertclassgroupofinterest",
            ),
        ),
        # 2. Remove the old InvertOrder.invert_class FK.
        migrations.RemoveField(
            model_name="invertorder",
            name="invert_class",
        ),
        # 3. Add the new unique constraint on InvertOrder(name, class_goi).
        migrations.AddConstraint(
            model_name="invertorder",
            constraint=models.UniqueConstraint(
                fields=["name", "class_goi"],
                name="unique_invertorder_name_class_goi",
            ),
        ),
        # 4. Drop the composite unique constraint on InvertClass(name, phylum).
        migrations.RemoveConstraint(
            model_name="invertclass",
            name="unique_invertclass_name_phylum",
        ),
        # 5. Remove InvertClass.phylum FK (no PROTECT issue: InvertClass no longer
        #    references InvertPhylum after this point, enabling deletion below).
        migrations.RemoveField(
            model_name="invertclass",
            name="phylum",
        ),
        # 6. Add unique=True on InvertClass.name (data is already unique after 0109).
        migrations.AlterField(
            model_name="invertclass",
            name="name",
            field=models.CharField(max_length=100, unique=True),
        ),
        # 7. Delete InvertPhylum data via InvertAttribute parent (cascade clears child rows).
        migrations.RunPython(delete_invert_phyla, migrations.RunPython.noop),
        # 8. Drop the now-empty invert_phylum table.
        migrations.DeleteModel(
            name="InvertPhylum",
        ),
    ]
