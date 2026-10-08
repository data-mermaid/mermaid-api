import hashlib

from django.db import migrations
from django.utils import timezone

# similar_name moved from UniqueManagementValidator to SimilarManagementNameValidator.
# Ignores are matched by validation_id (md5 of validator name, paths, level and type --
# see Validation._get_validation_id), so stored similar_name results are moved to the new
# validator's id. Otherwise ignored warnings come back (blocking submit), and the old id's
# ignore would silently apply to UniqueManagementValidator's not_unique_management warning.
SIMILAR_NAME_CODE = "similar_name"
OLD_NAME = "unique_management_validator"
NEW_NAME = "similar_management_name_validator"


def _validation_id(validator_name):
    key = f"{validator_name}::data.sample_event.management::field::value"
    return hashlib.md5(key.encode("utf-8")).hexdigest()


def move_similar_name_ignores(apps, schema_editor):
    CollectRecord = apps.get_model("api", "CollectRecord")
    old_id = _validation_id(OLD_NAME)
    new_id = _validation_id(NEW_NAME)
    now = timezone.now()

    qry = CollectRecord.objects.filter(
        validations__results__data__sample_event__management__contains=[
            {"validation_id": old_id, "code": SIMILAR_NAME_CODE}
        ]
    ).only("id", "validations")
    for collect_record in qry.iterator():
        validations = collect_record.validations
        for result in validations["results"]["data"]["sample_event"]["management"]:
            if result.get("validation_id") == old_id and result.get("code") == SIMILAR_NAME_CODE:
                result["name"] = NEW_NAME
                result["validation_id"] = new_id
        CollectRecord.objects.filter(id=collect_record.id).update(
            validations=validations, updated_on=now
        )


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0134_classifier_config"),
    ]

    operations = [
        migrations.RunPython(
            move_similar_name_ignores,
            reverse_code=migrations.RunPython.noop,
        )
    ]
