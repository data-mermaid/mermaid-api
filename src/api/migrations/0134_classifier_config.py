from django.db import migrations, models

# Reversing this migration re-adds num_points through AddField; 25 is the field default
# that backfills every existing row before NOT NULL is restored.
LEGACY_NUM_POINTS_DEFAULT = 25


def patch_size_to_config(apps, schema_editor):
    Classifier = apps.get_model("api", "Classifier")

    versions = list(Classifier.objects.values_list("version", flat=True))
    dupes = {v for v in versions if versions.count(v) > 1}
    if dupes:
        raise RuntimeError(
            f"Cannot apply unique constraint on Classifier.version; duplicates: {sorted(dupes)}"
        )

    non_default_num_points = {
        version: num_points
        for version, num_points in Classifier.objects.values_list("version", "num_points")
        if num_points != LEGACY_NUM_POINTS_DEFAULT
    }
    if non_default_num_points:
        raise RuntimeError(
            "Cannot drop Classifier.num_points; reverse migration backfills "
            f"{LEGACY_NUM_POINTS_DEFAULT} for every row and would overwrite these "
            f"non-default values: {non_default_num_points}"
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
                "Cannot reverse Classifier.config to patch_size; version "
                f"{classifier.version} has no patch_size in config and must be removed "
                "before this migration can be rolled back"
            )
        classifier.patch_size = config["patch_size"]
        classifier.save(update_fields=["patch_size"])


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
        # Nullable so the reverse path can re-add and backfill patch_size and num_points
        # before NOT NULL is restored on each.
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
        migrations.RemoveField(model_name="classifier", name="patch_size"),
        migrations.RemoveField(model_name="classifier", name="num_points"),
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
