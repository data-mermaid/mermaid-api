import pytest

from api.models import FISHBELT_PROTOCOL, CollectRecord, ProjectProfile


@pytest.fixture
def collect_record1(db_setup, project1, profile1):
    return CollectRecord.objects.create(
        project=project1, profile=profile1, data=dict()
    )


@pytest.fixture
def collect_record2(db_setup, project1, profile1):
    return CollectRecord.objects.create(
        project=project1, profile=profile1, data=dict()
    )


@pytest.fixture
def collect_record3(db_setup, project1, profile1):
    return CollectRecord.objects.create(
        project=project1, profile=profile1, data=dict()
    )



@pytest.fixture
def collect_record4(db_setup, project1, profile1, fish_size_bin_1, fish_species2, belt_transect_width_2m, management1, site1):
    data = {
        "protocol": FISHBELT_PROTOCOL,
        "sample_event": {
            "management": str(management1.pk),
            "site": str(site1.pk),
            "sample_date": "2019-12-3"
        },
        "obs_belt_fishes": [
            {
                "size": 51,
                "count": 3,
                "size_bin": str(fish_size_bin_1.pk),
                "fish_attribute": str(fish_species2.pk)
            }
        ],
        "observers": [
            {
                "id": None,
                "role": ProjectProfile.ADMIN,
                "profile": str(profile1.pk),
                "project": str(project1.pk),
                "is_admin": True,
                "created_by": None,
                "created_on": "2018-04-05T04:53:25.699076Z",
                "updated_by": "7901c943-5370-4896-a9ed-4b6ff5cb6ba0",
                "updated_on": "2018-06-28T05:07:21.414185Z",
                "is_collector": True,
                "profile_name": f"{profile1.first_name} {profile1.last_name}"
            }
        ],
        "fishbelt_transect": {
            "tide": None,
            "depth": 10,
            "width": str(belt_transect_width_2m.pk),
            "number": 10,
            "current": None,
            "size_bin": str(fish_size_bin_1.pk),
            "visibility": None,
            "sample_time": None,
            "len_surveyed": 100,
            "relative_depth": None
        },
        "sample_unit_method_id": "6bf3fc93-c08d-497d-98b7-9cb5994a1759"
    }

    validations = {
        "status": "ok",
        "results": {
        "null": {
            "validate_all_equal": {
                "status": "ok",
                "message": ""
            }
        },
        "site": {
            "wrapped": {
                "status": "ok",
                "message": ""
            },
            "validate_exists": {
                "status": "ok",
                "message": ""
            },
            "validate_system": {
                "status": "ok",
                "message": ""
            }
        },
        "depth": {
            "validate_range": {
            "status": "ok",
            "message": ""
            }
        },
        "observers": {
            "validate_list": {
            "status": "ok",
            "message": ""
            }
        },
        "management": {
            "wrapped": {
                "status": "ok",
                "message": ""
            },
            "validate_exists": {
                "status": "ok",
                "message": ""
            },
            "validate_system": {
                "status": "ok",
                "message": ""
            }
        },
        "sample_date": {
            "validate_system": {
                "status": "ok",
                "message": ""
            }
        },
        "sample_time": {
            "validate_system": {
                "status": "ok",
                "message": "Sample time is required"
            }
        },
        "len_surveyed": {
            "validate_range": {
                "status": "ok",
                "message": ""
            }
        },
        "obs_belt_fishes": {
            "validate_fish_count": {
                "status": "ignore",
                "message": "Total fish count less than 10"
            },
            "validate_observation_count": {
                "status": "ignore",
                "message": "Fewer than 5 observations"
            },
            "validate_observation_density": {
                "status": "ignore",
                "message": "Fish biomass less than 50 kg/ha"
            }
        },
        "fishbelt_transect": {
            "validate_duplicate": {
                "status": "ok",
                "message": ""
            }
        }
        },
        "last_validated": "2019-06-03 22:13:14.332342+00:00"
    }


    return CollectRecord.objects.create(
        project=project1, profile=profile1, data=data, stage=CollectRecord.VALIDATED_STAGE, validations=validations
    )
