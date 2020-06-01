import json
from api.submission.utils import validate_collect_records, submit_collect_records
from api.models import Profile
from api.resources.collect_record import CollectRecordSerializer

collect_record_ids = ["0f6fc251-1bc7-43c5-b7e0-2fc1ada53baa"]
profile_id = "0e6dc8a8-ae45-4c19-813c-6d688ed6a7c3"


def run():
    ignore_validations = {
        "len_surveyed": ["validate_range"],
        "obs_belt_fishes": [
            "validate_observation_count",
            "validate_observation_density",
            "validate_fish_count",
        ],
        "depth": ["validate_system", "validate_range"],
    }
    profile = Profile.objects.get(id=profile_id)
    results = validate_collect_records(
        profile=profile,
        record_ids=collect_record_ids,
        serializer_class=CollectRecordSerializer,
        validation_suppressants=ignore_validations,
    )

    for pk, result in results.items():
        print("result: {}".format(result["status"]))
        if result.get("status") == "ok":
            print(submit_collect_records(profile, collect_record_ids, ignore_validations))
