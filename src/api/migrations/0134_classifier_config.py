from django.db import migrations, models

# Un-applying this migration restores num_points as NOT NULL, so the reverse path needs a
# value for any row saved without one. 25 is what the column's field default supplies.
LEGACY_NUM_POINTS_DEFAULT = 25


def patch_size_to_config(apps, schema_editor):
    Classifier = apps.get_model("api", "Classifier")

    versions = list(Classifier.objects.values_list("version", flat=True))
    dupes = {v for v in versions if versions.count(v) > 1}
    if dupes:
        raise RuntimeError(
            f"Cannot apply unique constraint on Classifier.version; duplicates: {sorted(dupes)}"
        )

    for classifier in Classifier.objects.all():
        config = dict(classifier.config or {})
        config["patch_size"] = classifier.patch_size
        classifier.config = config
        classifier.save(update_fields=["config"])


def config_to_patch_size(apps, schema_editor):
    Classifier = apps.get_model("api", "Classifier")
    for classifier in Classifier.objects.all():
        config = classifier.config or {}
        if "patch_size" not in config:
            raise RuntimeError(
                f"Cannot reverse Classifier.config to patch_size; missing patch_size for version: {classifier.version}"
            )
        classifier.patch_size = config["patch_size"]
        # Rows saved while these fields are absent from model state carry NULL here.
        if classifier.num_points is None:
            classifier.num_points = LEGACY_NUM_POINTS_DEFAULT
        classifier.save(update_fields=["patch_size", "num_points"])


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0133_merge_20260817_1945"),
    ]

    operations = [
        migrations.AddField(
            model_name="classifier",
            name="classifier_type",
            field=models.CharField(
                choices=[("pyspacer", "pyspacer"), ("segmentation", "segmentation")],
                default="pyspacer",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="classifier",
            name="config",
            field=models.JSONField(blank=True, default=dict),
        ),
        # patch_size and num_points remain in the database: code that declares them must
        # keep reading them while two versions of the app run side by side. They are
        # nullable because the model does not declare them and supplies no value on
        # insert. Dropping the columns is a separate release (mermaid-classifier#98).
        migrations.AlterField(
            model_name="classifier",
            name="patch_size",
            field=models.IntegerField(help_text="Number of pixels", null=True),
        ),
        migrations.AlterField(
            model_name="classifier",
            name="num_points",
            field=models.IntegerField(default=LEGACY_NUM_POINTS_DEFAULT, null=True),
        ),
        migrations.RunPython(patch_size_to_config, config_to_patch_size),
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.RemoveField(model_name="classifier", name="patch_size"),
                migrations.RemoveField(model_name="classifier", name="num_points"),
            ],
            database_operations=[],
        ),
        migrations.AlterField(
            model_name="classifier",
            name="version",
            field=models.CharField(
                help_text="Classifier version (pattern: v[Version Number])",
                max_length=11,
                unique=True,
            ),
        ),
        # Runs after the backfill so existing rows already carry config["patch_size"].
        migrations.AddConstraint(
            model_name="classifier",
            constraint=models.CheckConstraint(
                condition=~models.Q(classifier_type="pyspacer")
                | models.Q(config__has_key="patch_size"),
                name="classifier_pyspacer_config_has_patch_size",
            ),
        ),
    ]
