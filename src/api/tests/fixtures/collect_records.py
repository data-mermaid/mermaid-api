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
def collect_record4_with_v2_validation(
    project1,
    profile1,
    fish_size_bin_1,
    fish_species2,
    belt_transect_width_2m,
    management1,
    site1,
    relative_depth1,
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
            "relative_depth": str(relative_depth1.pk),
        },
        "sample_unit_method_id": "6bf3fc93-c08d-497d-98b7-9cb5994a1759",
    }

    validations = {
        "version": "2",
        "status": "ok",
        "results": {
            "data": {
                "sample_event": {
                    "site": [
                        {
                            "name": "required_validator",
                            "status": "ok",
                            "code": None,
                            "context": None,
                            "validation_id": "e7ed8f2c1fddc46b13011a50bd2497ac",
                            "fields": ["data.sample_event.site"],
                        },
                        {
                            "name": "unique_site_validator",
                            "status": "ok",
                            "code": None,
                            "context": None,
                            "validation_id": "46227dd7ef79f00d8f3529859c5ebfd9",
                            "fields": ["data.sample_event.site"],
                        },
                    ],
                    "management": [
                        {
                            "name": "required_validator",
                            "status": "ok",
                            "code": None,
                            "context": None,
                            "validation_id": "51aa29c32842e2df62bdf4cfdb790943",
                            "fields": ["data.sample_event.management"],
                        },
                        {
                            "name": "unique_management_validator",
                            "status": "ok",
                            "code": None,
                            "context": None,
                            "validation_id": "970d0593a68c6432ff2e439f8df1dbaf",
                            "fields": ["data.sample_event.management"],
                        },
                    ],
                    "sample_date": [
                        {
                            "name": "required_validator",
                            "status": "ok",
                            "code": None,
                            "context": None,
                            "validation_id": "0beda41c3b904d1b48732d1039cec880",
                            "fields": ["data.sample_event.sample_date"],
                        },
                        {
                            "name": "sample_date_validator",
                            "status": "ok",
                            "code": None,
                            "context": None,
                            "validation_id": "aae43ffdcdd2f62dcbd2923cdbcdd066",
                            "fields": ["data.sample_event.sample_date"],
                        },
                    ],
                },
                "fishbelt_transect": {
                    "number": [
                        {
                            "name": "required_validator",
                            "status": "ok",
                            "code": None,
                            "context": None,
                            "validation_id": "b0781708804d47a9816741c010587f88",
                            "fields": ["data.fishbelt_transect.number"],
                        }
                    ],
                    "width": [
                        {
                            "name": "required_validator",
                            "status": "ok",
                            "code": None,
                            "context": None,
                            "validation_id": "9271ae54919816ddb8026d64522ba35f",
                            "fields": ["data.fishbelt_transect.width"],
                        }
                    ],
                    "relative_depth": [
                        {
                            "name": "required_validator",
                            "status": "ok",
                            "code": "",
                            "context": None,
                            "validation_id": "70b253a45f4e34b8da73e2f699ae4754",
                            "fields": ["data.fishbelt_transect.relative_depth"],
                        }
                    ],
                    "depth": [
                        {
                            "name": "required_validator",
                            "status": "ok",
                            "code": None,
                            "context": None,
                            "validation_id": "79e2d4a20bf38ef2f508503e7c125c4d",
                            "fields": ["data.fishbelt_transect.depth"],
                        },
                        {
                            "name": "depth_validator",
                            "status": "ok",
                            "code": None,
                            "context": None,
                            "validation_id": "01390e7d2cda542b47b2be2eb15d25c6",
                            "fields": ["data.fishbelt_transect.depth"],
                        },
                    ],
                    "size_bin": [
                        {
                            "name": "required_validator",
                            "status": "ok",
                            "code": None,
                            "context": None,
                            "validation_id": "7ef514ed41d46f3e6e3f2e70a8fa6a68",
                            "fields": ["data.fishbelt_transect.size_bin"],
                        }
                    ],
                    "sample_time": [
                        {
                            "name": "sample_time_validator",
                            "status": "ok",
                            "code": None,
                            "context": None,
                            "validation_id": "54a37d1511e3e31b3abe1b3ea3f93357",
                            "fields": ["data.fishbelt_transect.sample_time"],
                        }
                    ],
                    "len_surveyed": [
                        {
                            "name": "len_surveyed_validator",
                            "status": "ok",
                            "code": None,
                            "context": None,
                            "validation_id": "a2a519988d604f3ce9d82519178fbb92",
                            "fields": ["data.fishbelt_transect.len_surveyed"],
                        }
                    ],
                },
                "obs_belt_fishes": [
                    [
                        {
                            "name": "fish_family_subset_validator",
                            "status": "ok",
                            "code": None,
                            "context": None,
                            "validation_id": "fcb7300140f0df8b9a794fa286549bd2",
                            "fields": ["data.obs_belt_fishes"],
                        },
                        {
                            "name": "fish_size_validator",
                            "status": "ignore",
                            "code": "max_fish_size",
                            "context": {"max_length": 32.0},
                            "validation_id": "2b289dc99c02e9ae1c764e8a71cca3cc",
                            "fields": ["data.obs_belt_fishes"],
                        },
                        {
                            "name": "fish_count_validator",
                            "status": "ok",
                            "code": None,
                            "context": None,
                            "validation_id": "ccb38683efc25838ec9b7ff026e78a19",
                            "fields": ["data.obs_belt_fishes"],
                        },
                        {
                            "name": "region_validator",
                            "status": "ok",
                            "code": None,
                            "context": None,
                            "validation_id": "7f208a0e498e687f5239e728cff465c5",
                            "fields": ["data.obs_belt_fishes"],
                        },
                        {
                            "name": "fish_attribute_list_required_validator",
                            "status": "ok",
                            "code": None,
                            "context": None,
                            "validation_id": "c6dbcae3727618d98cd8f9fb59e23713",
                            "fields": ["data.obs_belt_fishes"],
                        },
                        {
                            "name": "size_list_required_validator",
                            "status": "ok",
                            "code": None,
                            "context": None,
                            "validation_id": "1c7d285f0b8be156f3ac7256e5271c8a",
                            "fields": ["data.obs_belt_fishes"],
                        },
                        {
                            "name": "count_list_required_validator",
                            "status": "ok",
                            "code": None,
                            "context": None,
                            "validation_id": "97ab88b432ed6ccf204b833e912aa26b",
                            "fields": ["data.obs_belt_fishes"],
                        },
                    ]
                ],
                "observers": [
                    {
                        "name": "required_validator",
                        "status": "ok",
                        "code": None,
                        "context": None,
                        "validation_id": "c42a16612631db8b3f551e827f44703d",
                        "fields": ["data.observers"],
                    }
                ],
            },
            "$record": [
                {
                    "name": "total_fish_count_validator",
                    "status": "ignore",
                    "code": "minimum_total_fish_count",
                    "context": {"minimum_fish_count": 10},
                    "validation_id": "8fb039422eb29127929941ef86b64036",
                    "fields": ["data.obs_belt_fishes"],
                },
                {
                    "name": "observation_count_validator",
                    "status": "ignore",
                    "code": "too_few_observations",
                    "context": {"observation_count_range": [5, 200]},
                    "validation_id": "63043489232e671a4f9231fdf6d2665f",
                    "fields": ["data.obs_belt_fishes"],
                },
                {
                    "name": "biomass_validator",
                    "status": "ignore",
                    "code": "low_density",
                    "context": {"biomass_range": [50, 5000]},
                    "validation_id": "fc7bf1e4ab2897e8749fd2030cbbc30c",
                    "fields": ["data.obs_belt_fishes"],
                },
                {
                    "name": "unique_transect_validator",
                    "status": "ok",
                    "code": None,
                    "context": None,
                    "validation_id": "e7285cf5c4f441bdffdce83461c12d69",
                    "fields": [
                        "data.fishbelt_transect.label",
                        "data.fishbelt_transect.number",
                        "data.fishbelt_transect.width",
                        "data.fishbelt_transect.relative_depth",
                        "data.fishbelt_transect.depth",
                        "data.sample_event.site",
                        "data.sample_event.management",
                        "data.sample_event.sample_date",
                    ],
                },
                {
                    "name": "all_equal_validator",
                    "status": "ok",
                    "code": None,
                    "context": None,
                    "validation_id": "9175eb636ead3bc01a94378fe4d48af8",
                    "fields": ["data.obs_belt_fishes"],
                },
                {
                    "name": "dry_submit_validator",
                    "status": "ok",
                    "code": None,
                    "context": None,
                    "validation_id": "ba4ac7677b7878d0a321cd3913f264ca",
                    "fields": ["__all__"],
                },
            ],
        },
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
    relative_depth1,
):
    observations = [
        dict(
            count="10",
            fish_attribute=str(fish_species1.id),
            size=17.5,
        ),
        dict(
            count="15",
            fish_attribute=str(fish_species1.id),
            size=17.5,
        ),
        dict(
            count="20",
            fish_attribute=str(fish_species1.id),
            size=17.5,
        ),
        dict(
            count="30",
            fish_attribute=str(fish_species1.id),
            size=17.5,
        ),
        dict(
            count="35",
            fish_attribute=str(fish_species1.id),
            size=17.5,
        ),
        dict(
            count="40",
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
            relative_depth=str(relative_depth1.id),
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
            size=1999,
        ),
    ]

    data_warn["obs_belt_fishes"] = observations
    data_warn["fishbelt_transect"]["len_surveyed"] = 101
    data_warn["fishbelt_transect"]["depth"] = 50.0
    data_warn["fishbelt_transect"]["sample_time"] = "5:00"

    return CollectRecord.objects.create(
        project=project1,
        profile=profile1,
        stage=CollectRecord.VALIDATED_STAGE,
        data=data_warn,
    )


@pytest.fixture
def invalid_collect_record_null_str_warn(
    project1, profile1, valid_collect_record, fish_species1
):
    data_warn = valid_collect_record.data
    observations = [
        dict(
            count="10",
            fish_attribute=str(fish_species1.id),
            size="17.5",
        ),
        dict(
            count="15",
            fish_attribute=str(fish_species1.id),
            size="17.5",
        ),
        dict(
            count="20",
            fish_attribute=str(fish_species1.id),
            size="17.5",
        ),
    ]

    data_warn["obs_belt_fishes"] = observations
    data_warn["fishbelt_transect"]["len_surveyed"] = "101"
    data_warn["fishbelt_transect"]["depth"] = "31"
    data_warn["fishbelt_transect"]["sample_time"] = "5:00"
    data_warn["fishbelt_transect"]["relative_depth"] = ""

    return CollectRecord.objects.create(
        project=project1,
        profile=profile1,
        stage=CollectRecord.VALIDATED_STAGE,
        data=data_warn,
    )


@pytest.fixture
def invalid_collect_record_error(
    project1, profile1, valid_collect_record, sample_event2, fish_species1, fish_species2
):
    data_error = valid_collect_record.data
    data_error["observers"] = None
    data_error["sample_event"]["sample_date"] = (
        '2021-9-<font style="vertical-align: inherit;">'
        + '<font style="vertical-align: inherit;">24</font></font>'
    )
    data_error["obs_belt_fishes"][0]["size"] = 10000
    data_error["obs_belt_fishes"][1]["size"] = ""
    data_error["obs_belt_fishes"][2]["size"] = None
    data_error["obs_belt_fishes"][2]["fish_attribute"] = str(fish_species2.pk)

    data_error["sample_event"] = dict(
        management=str(sample_event2.management.id),
        site=str(sample_event2.site.id),
        sample_date='2021-9-<font style="vertical-align: inherit;"><font style="vertical-align: inherit;">24</font></font>',
    )

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
