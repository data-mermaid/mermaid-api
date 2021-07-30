import pytest

from api.models import FISHBELT_PROTOCOL, CollectRecord, ProjectProfile


@pytest.fixture
def collect_record1(project1, profile1):
    return CollectRecord.objects.create(project=project1, profile=profile1, data=dict())


@pytest.fixture
def collect_record2(project1, profile1):
    return CollectRecord.objects.create(project=project1, profile=profile1, data=dict())


@pytest.fixture
def collect_record3(project1, profile1):
    return CollectRecord.objects.create(project=project1, profile=profile1, data=dict())


@pytest.fixture
def collect_record4(
    project1,
    profile1,
    fish_size_bin_1,
    fish_species2,
    belt_transect_width_2m,
    management1,
    site1,
):
    data = {
        "protocol": FISHBELT_PROTOCOL,
        "sample_event": {
            "management": str(management1.pk),
            "site": str(site1.pk),
            "sample_date": "2019-12-3",
        },
        "obs_belt_fishes": [
            {"size": 51, "count": 3, "fish_attribute": str(fish_species2.pk)}
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
                "profile_name": f"{profile1.first_name} {profile1.last_name}",
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
            "relative_depth": None,
        },
        "sample_unit_method_id": "6bf3fc93-c08d-497d-98b7-9cb5994a1759",
    }

    validations = {
        "status": "ok",
        "results": {
            "null": {"validate_all_equal": {"status": "ok", "message": ""}},
            "site": {
                "wrapped": {"status": "ok", "message": ""},
                "validate_exists": {"status": "ok", "message": ""},
                "validate_system": {"status": "ok", "message": ""},
            },
            "depth": {"validate_range": {"status": "ok", "message": ""}},
            "observers": {"validate_list": {"status": "ok", "message": ""}},
            "management": {
                "wrapped": {"status": "ok", "message": ""},
                "validate_exists": {"status": "ok", "message": ""},
                "validate_system": {"status": "ok", "message": ""},
            },
            "sample_date": {"validate_system": {"status": "ok", "message": ""}},
            "sample_time": {
                "validate_system": {
                    "status": "ok",
                    "message": "Sample time is required",
                }
            },
            "len_surveyed": {"validate_range": {"status": "ok", "message": ""}},
            "obs_belt_fishes": {
                "validate_fish_count": {
                    "status": "ignore",
                    "message": "Total fish count less than 10",
                },
                "validate_observation_count": {
                    "status": "ignore",
                    "message": "Fewer than 5 observations",
                },
                "validate_observation_density": {
                    "status": "ignore",
                    "message": "Fish biomass less than 50 kg/ha",
                },
            },
            "fishbelt_transect": {
                "validate_duplicate": {"status": "ok", "message": ""}
            },
        },
        "last_validated": "2019-06-03 22:13:14.332342+00:00",
    }

    return CollectRecord.objects.create(
        project=project1,
        profile=profile1,
        data=data,
        stage=CollectRecord.VALIDATED_STAGE,
        validations=validations,
    )


@pytest.fixture
def valid_collect_record(
    sample_event1,
    belt_transect_width_5m,
    fish_species1,
    project1,
    profile1,
    project_profile1,
    fish_size_bin_1,
):
    observations = [
        dict(
            count=10,
            fish_attribute=str(fish_species1.id),
            size=17.5,
        ),
        dict(
            count=15,
            fish_attribute=str(fish_species1.id),
            size=17.5,
        ),
        dict(
            count=20,
            fish_attribute=str(fish_species1.id),
            size=17.5,
        ),
        dict(
            count=30,
            fish_attribute=str(fish_species1.id),
            size=17.5,
        ),
        dict(
            count=35,
            fish_attribute=str(fish_species1.id),
            size=17.5,
        ),
        dict(
            count=40,
            fish_attribute=str(fish_species1.id),
            size=17.5,
        ),
    ]
    data_ok = dict(
        protocol="fishbelt",
        obs_belt_fishes=observations,
        fishbelt_transect=dict(
            width=str(belt_transect_width_5m.id),
            number=1,
            len_surveyed=100,
            depth=1,
            size_bin=str(fish_size_bin_1.id),
        ),
        sample_event=dict(
            management=str(sample_event1.management.id),
            site=str(sample_event1.site.id),
            sample_date=f"{sample_event1.sample_date.year}-{sample_event1.sample_date.month}-{sample_event1.sample_date.day}",
        ),
        observers=[{"profile": str(project_profile1.profile.id)}],
    )
    return CollectRecord.objects.create(
        project=project1,
        profile=profile1,
        stage=CollectRecord.VALIDATED_STAGE,
        data=data_ok,
    )


@pytest.fixture
def invalid_collect_record_warn(
    project1, profile1, valid_collect_record, fish_species1
):
    data_warn = valid_collect_record.data
    observations = [
        dict(
            count=10,
            fish_attribute=str(fish_species1.id),
            size=17.5,
        ),
        dict(
            count=15,
            fish_attribute=str(fish_species1.id),
            size=17.5,
        ),
        dict(
            count=20,
            fish_attribute=str(fish_species1.id),
            size=17.5,
        ),
    ]

    data_warn["obs_belt_fishes"] = observations
    data_warn["sample_event"]["depth"] = 50.0
    data_warn["fishbelt_transect"]["len_surveyed"] = 101
    data_warn["fishbelt_transect"]["depth"] = 31
    data_warn["fishbelt_transect"]["sample_time"] = "5:00"

    return CollectRecord.objects.create(
        project=project1,
        profile=profile1,
        stage=CollectRecord.VALIDATED_STAGE,
        data=data_warn,
    )


@pytest.fixture
def invalid_collect_record_error(
    project1, profile1, valid_collect_record, fish_species1
):
    data_error = valid_collect_record.data
    data_error["observers"] = None

    return CollectRecord.objects.create(
        project=project1,
        profile=profile1,
        stage=CollectRecord.VALIDATED_STAGE,
        data=data_error,
    )


@pytest.fixture
def valid_benthic_lit_collect_record(
    benthic_attribute_3,
    benthic_attribute_4,
    project1,
    profile1,
    project_profile1,
    sample_event1,
):
    observations = [
        dict(attribute=str(benthic_attribute_3.id), length=1000),
        dict(attribute=str(benthic_attribute_3.id), length=1500),
        dict(attribute=str(benthic_attribute_3.id), length=2000),
        dict(attribute=str(benthic_attribute_3.id), length=2500),
        dict(attribute=str(benthic_attribute_4.id), length=3000),
    ]
    data_ok = dict(
        protocol="benthiclit",
        obs_benthic_lits=observations,
        benthic_transect=dict(depth=1, number=2, len_surveyed=100),
        sample_event=dict(
            management=str(sample_event1.management.id),
            site=str(sample_event1.site.id),
            sample_date=f"{sample_event1.sample_date:%Y-%m-%d}",
        ),
        observers=[{"profile": str(profile1.id)}],
    )
    return CollectRecord.objects.create(
        project=project1,
        profile=profile1,
        stage=CollectRecord.VALIDATED_STAGE,
        data=data_ok,
    )


@pytest.fixture
def invalid_benthic_lit_collect_record(
    benthic_attribute_3,
    project1,
    profile1,
    project_profile1,
    sample_event1,
):
    observations = [
        dict(attribute=str(benthic_attribute_3.id), length=1000),
        dict(attribute=str(benthic_attribute_3.id), length=1500),
        dict(attribute=str(benthic_attribute_3.id), length=2000),
    ]
    data_error = dict(
        protocol="benthiclit",
        obs_benthic_lits=observations,
        benthic_transect=dict(depth=1, number=2, len_surveyed=100),
        sample_event=dict(
            management=str(sample_event1.management.id),
            site=str(sample_event1.site.id),
            sample_date=f"{sample_event1.sample_date:%Y-%m-%d}",
        ),
        observers=[{"profile": str(profile1.id)}],
    )
    return CollectRecord.objects.create(
        project=project1,
        profile=profile1,
        stage=CollectRecord.VALIDATED_STAGE,
        data=data_error,
    )


@pytest.fixture
def valid_benthic_pit_collect_record(
    benthic_attribute_3,
    benthic_attribute_4,
    project1,
    profile1,
    project_profile1,
    sample_event1,
):
    observations = [
        dict(attribute=str(benthic_attribute_3.id), interval=5),
        dict(attribute=str(benthic_attribute_3.id), interval=10),
        dict(attribute=str(benthic_attribute_3.id), interval=15),
        dict(attribute=str(benthic_attribute_3.id), interval=20),
        dict(attribute=str(benthic_attribute_3.id), interval=25),
        dict(attribute=str(benthic_attribute_4.id), interval=30),
    ]
    data = dict(
        protocol="benthicpit",
        obs_benthic_pits=observations,
        benthic_transect=dict(depth=1, number=1, len_surveyed=30),
        interval_size=5,
        interval_start=5,
        sample_event=dict(
            management=str(sample_event1.management.id),
            site=str(sample_event1.site.id),
            sample_date=f"{sample_event1.sample_date:%Y-%m-%d}",
        ),
        observers=[{"profile": str(profile1.id)}],
    )
    return CollectRecord.objects.create(
        project=project1,
        profile=profile1,
        stage=CollectRecord.VALIDATED_STAGE,
        data=data,
    )


@pytest.fixture
def invalid_benthic_pit_collect_record(
    benthic_attribute_3,
    project1,
    profile1,
    project_profile1,
    sample_event1,
):
    observations = [
        dict(attribute=str(benthic_attribute_3.id), length=1000),
        dict(attribute=str(benthic_attribute_3.id), length=1500),
        dict(attribute=str(benthic_attribute_3.id), length=2000),
    ]

    data = dict(
        protocol="benthicpit",
        obs_benthic_pits=observations,
        benthic_transect=dict(depth=1, number=1, len_surveyed=30),
        interval_size=5,
        interval_start=5,
        sample_event=dict(
            management=str(sample_event1.management.id),
            site=str(sample_event1.site.id),
            sample_date=f"{sample_event1.sample_date:%Y-%m-%d}",
        ),
        observers=[{"profile": str(profile1.id)}],
    )

    return CollectRecord.objects.create(
        project=project1,
        profile=profile1,
        stage=CollectRecord.VALIDATED_STAGE,
        data=data,
    )


@pytest.fixture
def valid_habitat_complexity_collect_record(
    sample_event1,
    habitat_complexity_score1,
    project1,
    profile1,
    project_profile1,
):
    observations = [
        dict(score=str(habitat_complexity_score1.id), interval=0),
        dict(score=str(habitat_complexity_score1.id), interval=5),
        dict(score=str(habitat_complexity_score1.id), interval=10),
        dict(score=str(habitat_complexity_score1.id), interval=15),
        dict(score=str(habitat_complexity_score1.id), interval=20),
        dict(score=str(habitat_complexity_score1.id), interval=25),
    ]
    data = dict(
        protocol="habitatcomplexity",
        obs_habitat_complexities=observations,
        benthic_transect=dict(depth=1, number=2, len_surveyed=30),
        interval_size=5,
        sample_event=dict(
            management=str(sample_event1.management.id),
            site=str(sample_event1.site.id),
            sample_date=f"{sample_event1.sample_date:%Y-%m-%d}",
        ),
        observers=[{"profile": str(profile1.id)}],
    )

    return CollectRecord.objects.create(
        project=project1,
        profile=profile1,
        stage=CollectRecord.VALIDATED_STAGE,
        data=data,
    )


@pytest.fixture
def invalid_habitat_complexity_collect_record(
    sample_event1,
    habitat_complexity_score1,
    project1,
    profile1,
    project_profile1,
):
    observations = [
        dict(score="invalid score id", interval=0),
        dict(score=str(habitat_complexity_score1.id), interval=5),
        dict(score=str(habitat_complexity_score1.id), interval=10),
        dict(score=str(habitat_complexity_score1.id), interval=15),
        dict(score=str(habitat_complexity_score1.id), interval=20),
        dict(score=str(habitat_complexity_score1.id), interval=25),
    ]
    data = dict(
        protocol="habitatcomplexity",
        obs_habitat_complexities=observations,
        benthic_transect=dict(depth=1, number=2, len_surveyed=30),
        interval_size=5,
        sample_event=dict(
            management=str(sample_event1.management.id),
            site=str(sample_event1.site.id),
            sample_date=f"{sample_event1.sample_date:%Y-%m-%d}",
        ),
        observers=[{"profile": str(profile1.id)}],
    )

    return CollectRecord.objects.create(
        project=project1,
        profile=profile1,
        stage=CollectRecord.VALIDATED_STAGE,
        data=data,
    )
