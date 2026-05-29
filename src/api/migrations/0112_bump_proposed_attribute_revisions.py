from django.db import migrations
from django.utils import timezone

PROPOSED = 10


def bump_proposed_attribute_revisions(apps, schema_editor):
    now = timezone.now()
    for model_name in [
        "BenthicAttribute",
        "FishSpecies",
        "FishGenus",
        "FishFamily",
        "FishGrouping",
    ]:
        model = apps.get_model("api", model_name)
        model.objects.filter(status=PROPOSED).update(updated_on=now)


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0111_remove_group_of_interest_from_invert_species"),
    ]

    operations = [
        migrations.RunPython(
            bump_proposed_attribute_revisions,
            reverse_code=migrations.RunPython.noop,
        )
    ]
