from django.db import migrations, models


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
        classifier.patch_size = (classifier.config or {}).get("patch_size") or 0
        classifier.save(update_fields=["patch_size"])


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0129_merge_20260701_1228"),
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
    ]
