import django.db.models.deletion
from django.db import migrations, models


def delete_invert_class_group_of_interest(apps, schema_editor):
    """Delete all InvertClassGroupOfInterest rows via their InvertAttribute parent.

    Must run after RemoveField(invertorder, class_goi) so that the PROTECT FK from
    InvertOrder no longer blocks deletion.
    """
    InvertAttribute = apps.get_model("api", "InvertAttribute")
    InvertClassGroupOfInterest = apps.get_model("api", "InvertClassGroupOfInterest")
    attr_ids = list(
        InvertClassGroupOfInterest.objects.values_list("invertattribute_ptr_id", flat=True)
    )
    InvertAttribute.objects.filter(pk__in=attr_ids).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0114_goi_data"),
    ]

    operations = [
        # 1. Make InvertGenus.group_of_interest non-nullable (all rows populated in 0114).
        migrations.AlterField(
            model_name="invertgenus",
            name="group_of_interest",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                to="api.invertgroupofinterest",
            ),
        ),
        # 2. Make InvertOrder.invert_class non-nullable (all rows populated in 0114).
        migrations.AlterField(
            model_name="invertorder",
            name="invert_class",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="orders",
                to="api.invertclass",
            ),
        ),
        # 3. Remove the old class_goi FK from InvertOrder.
        #    This unblocks deletion of InvertClassGroupOfInterest rows in step 4.
        migrations.RemoveField(
            model_name="invertorder",
            name="class_goi",
        ),
        # 4. Delete InvertClassGroupOfInterest rows (and their InvertAttribute parents).
        #    Safe now that no InvertOrder rows reference them.
        migrations.RunPython(
            delete_invert_class_group_of_interest,
            migrations.RunPython.noop,
        ),
        # 5. Re-add unique constraint on InvertOrder(name, invert_class).
        migrations.AddConstraint(
            model_name="invertorder",
            constraint=models.UniqueConstraint(
                fields=["name", "invert_class"],
                name="unique_invertorder_name_invert_class",
            ),
        ),
        # 6. Re-add unique constraint on InvertFamily(name, order) — safe now that
        #    Muricidae is no longer duplicated.
        migrations.AddConstraint(
            model_name="invertfamily",
            constraint=models.UniqueConstraint(
                fields=["name", "order"],
                name="unique_invertfamily_name_order",
            ),
        ),
        # 7. Promote invertattribute_ptr to PK on InvertGroupOfInterest.
        #
        #    Django cannot drop a primary key column directly, so this uses
        #    SeparateDatabaseAndState:
        #      - Database side: raw SQL to swap the PK and restore the FK from
        #        invert_genus (which is cascade-dropped when id is dropped).
        #      - State side: delete + recreate the model with the correct MTI bases
        #        so future makemigrations detects no drift.
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql="""
                    -- Drop id column; CASCADE drops the old PK constraint and all FK
                    -- constraints from other tables that reference invert_group_of_interest(id).
                    ALTER TABLE invert_group_of_interest DROP COLUMN id CASCADE;

                    -- Make invertattribute_ptr_id the new primary key.
                    ALTER TABLE invert_group_of_interest
                        ADD PRIMARY KEY (invertattribute_ptr_id);

                    -- Restore the FK from invert_genus.group_of_interest_id.
                    -- The UUID values are unchanged (same UUIDs used for both id and
                    -- invertattribute_ptr_id in migration 0114), so no data updates needed.
                    ALTER TABLE invert_genus
                        ADD CONSTRAINT invert_genus_group_of_interest_id_fk
                        FOREIGN KEY (group_of_interest_id)
                        REFERENCES invert_group_of_interest (invertattribute_ptr_id);
                    """,
                    reverse_sql=migrations.RunSQL.noop,
                ),
            ],
            state_operations=[
                # Recreate InvertGroupOfInterest as a proper InvertAttribute MTI child
                # so that the migration state matches the model code.
                migrations.DeleteModel(name="InvertGroupOfInterest"),
                migrations.CreateModel(
                    name="InvertGroupOfInterest",
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
                        ("name", models.CharField(max_length=100, unique=True)),
                    ],
                    options={
                        "verbose_name": "macroinvertebrate group of interest",
                        "verbose_name_plural": "macroinvertebrate groups of interest",
                        "db_table": "invert_group_of_interest",
                        "ordering": ("name",),
                    },
                    bases=("api.invertattribute",),
                ),
            ],
        ),
        # 8. Drop the now-empty invert_class_goi table.
        migrations.DeleteModel(
            name="InvertClassGroupOfInterest",
        ),
    ]
