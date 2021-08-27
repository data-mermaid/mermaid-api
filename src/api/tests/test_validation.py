import datetime

import pytest
from django.contrib.gis.geos import Point

from api.models import (
    BenthicAttribute,
    BenthicTransect,
    HabitatComplexityScore,
    Management,
    SampleEvent,
    Site,
)
from api.submission.validations import (
    ERROR,
    IGNORE,
    OK,
    WARN,
    BenthicTransectValidation,
    EmptyListValidation,
    ManagementValidation,
    ObsBenthicLITValidation,
    ObsBenthicPercentCoveredValidation,
    ObsColoniesBleachedValidation,
    ObservationsValidation,
    ObserverValidation,
    ObsFishBeltValidation,
    ObsHabitatComplexitiesValidation,
    SiteValidation,
    ValueInRangeValidation,
)


def test_empty_list_validation():
    # OK
    validation = EmptyListValidation("abc", [1, 2, 3], "List is valid")
    assert validation.validate() == OK

    # Error: list is none
    validation = EmptyListValidation("abc", None, "List is None")
    assert validation.validate() == ERROR

    # Error: list is empty
    validation = EmptyListValidation("abc", [], "List is empty")
    assert validation.validate() == ERROR


def test_value_in_range_validation():
    # OK
    validation = ValueInRangeValidation(identifier="abc", value=5, value_range=(0, 10))
    assert validation.validate() == OK

    # OK
    validation = ValueInRangeValidation(identifier="abc", value=0, value_range=(0, 10))
    assert validation.validate() == OK

    # ERROR
    validation = ValueInRangeValidation(
        identifier="abc",
        value=0,
        value_range=(0, 10),
        value_range_operators=("<=", ">"),
    )
    assert validation.validate() == ERROR

    # OK
    validation = ValueInRangeValidation(identifier="abc", value=10, value_range=(0, 10))
    assert validation.validate() == OK

    # ERROR
    validation = ValueInRangeValidation(
        identifier="abc",
        value=10,
        value_range=(0, 10),
        value_range_operators=("<", ">="),
    )
    assert validation.validate() == ERROR

    # ERROR
    validation = ValueInRangeValidation(identifier="abc", value=11, value_range=(0, 10))
    assert validation.validate() == ERROR


def test_site_validation(
    site1, project1, country1, reef_type1, reef_exposure1, reef_zone1
):
    validation = SiteValidation(str(site1.pk))
    assert validation.validate() == OK

    # Invalid uuid test
    validation = SiteValidation(str("not-uuid"))
    assert validation.validate() == ERROR

    # Site doesn't exist test
    uuid = str("61bd9485-db2b-4e7d-8fe9-3c34b371ed0f")
    validation = SiteValidation(uuid)
    assert validation.validate() == ERROR

    site3 = None
    try:
        site3 = Site.objects.create(
            project=project1,
            name="site ab",
            location=Point(1, 1, srid=4326),
            country=country1,
            reef_type=reef_type1,
            exposure=reef_exposure1,
            reef_zone=reef_zone1,
        )

        validation = SiteValidation(str(site1.pk))
        validation.validate()
        validation.ignore_warning(SiteValidation.identifier, "validate_similar")

        retry_validation = SiteValidation(
            str(site1.pk), previous_validations=validation.logs["site"]
        )
        retry_validation.validate()
        retry_validation_logs = retry_validation.logs

        assert (
            retry_validation_logs[SiteValidation.identifier]["validate_similar"][
                "status"
            ]
            == IGNORE
        )
    finally:
        if site3:
            site3.delete()


def test_management_validation(management1, project1, site1):
    validation = ManagementValidation(str(management1.pk))
    assert validation.validate() == OK

    # Invalid uuid test
    validation = ManagementValidation(str("not-uuid"))
    assert validation.validate() == ERROR

    # Management doesn't exist test
    uuid = str("61bd9485-db2b-4e7d-8fe9-3c34b371ed0f")
    validation = ManagementValidation(uuid)
    assert validation.validate() == ERROR

    mgmt2 = None
    se2 = None
    benthic_transect = None

    try:
        mgmt2 = Management.objects.create(
            project=project1,
            est_year=2000,
            name="Test Management",
            notes="Hey what is up",
        )

        se2 = SampleEvent.objects.create(
            site=site1,
            management=mgmt2,
            sample_date=datetime.date(2018, 7, 13),
        )

        benthic_transect = BenthicTransect.objects.create(
            number=1, len_surveyed=100, sample_event=se2
        )

        management_validation = ManagementValidation(str(management1.pk))
        management_validation.validate()

        management_validation.ignore_warning(
            ManagementValidation.identifier, "validate_similar"
        )

        retry_validation = ManagementValidation(
            str(management1.pk),
            previous_validations=management_validation.logs[
                ManagementValidation.identifier
            ],
        )
        retry_validation.validate()
        retry_validation_logs = retry_validation.logs

        assert (
            retry_validation_logs[ManagementValidation.identifier]["validate_similar"][
                "status"
            ]
            == IGNORE
        )

    finally:
        if benthic_transect:
            benthic_transect.delete()
        if mgmt2:
            mgmt2.delete()


def test_observer_validation():
    # Observer doesn't exist test
    uuid = str("61bd9485-db2b-4e7d-8fe9-3c34b371ed00")
    validation = ObserverValidation(uuid)
    validation.validate() == ERROR


def test_observations_validation():
    valid_observations = [
        dict(interval=1, score="test1"),
        dict(interval=2, score="test2"),
        dict(interval=3, score="test3"),
    ]
    validation = ObservationsValidation(
        dict(obs_habitat_complexities=valid_observations)
    )
    assert validation.validate_all_equal() == OK

    invalid_observations = [
        dict(interval=1, score="test1"),
        dict(interval=1, score="test1"),
        dict(interval=1, score="test1"),
    ]
    validation = ObservationsValidation(
        dict(obs_habitat_complexities=invalid_observations)
    )
    assert validation.validate_all_equal() == WARN


def test_benthic_transect_validation(
    site1,
    management1,
    sample_event1,
    benthic_transect1,
    benthic_pit1,
    current1,
    relative_depth1,
    tide1,
    reef_slope1,
    visibility1,
):
    sample_event = {
        "site": str(benthic_transect1.sample_event.site.id),
        "management": str(benthic_transect1.sample_event.management.id),
        "sample_date": benthic_transect1.sample_event.sample_date,
    }

    benthic_transect = {
        "sample_event": sample_event,
        "current": str(current1.id),
        "reef_slope": str(reef_slope1.id),
        "relative_depth": str(relative_depth1.id),
        "tide": str(tide1),
        "visibility": str(visibility1.id),
        "depth": benthic_transect1.depth,
        "len_surveyed": benthic_transect1.len_surveyed,
        "sample_time": benthic_transect1.sample_time,
        "number": benthic_transect1.number,
    }

    validation = BenthicTransectValidation(
        {
            "protocol": "benthicpit",
            "sample_event": sample_event,
            "benthic_transect": benthic_transect,
        }
    )
    assert validation.validate_duplicate() == WARN

    # invalid missing id
    sample_event_2 = dict(relative_depth="")
    validation = BenthicTransectValidation(
        {
            "sample_event": sample_event_2,
            "benthic_transect": benthic_transect,
        }
    )
    assert validation.validate_duplicate() == ERROR

    benthic_transect2 = dict(number=2)
    validation = BenthicTransectValidation(
        {
            "sample_event": sample_event,
            "benthic_transect": benthic_transect2,
        }
    )
    assert validation.validate_duplicate() == OK

    # valid data different transect method
    validation = BenthicTransectValidation(
        {
            "protocol": "benthiclit",
            "sample_event": sample_event,
            "benthic_transect": benthic_transect,
        }
    )
    assert validation.validate_duplicate() == OK


def test_obs_fish_belt_validation(
    belt_transect_width_2m,
    belt_transect_width_condition1,
    obs_belt_fishes_valid,
    obs_belt_fishes_invalid,
    obs_belt_fishes_low_biomass_invalid,
    obs_belt_fishes_high_biomass_invalid,
    obs_belt_fishes_biomass_valid,
):
    fishbelt_transect = dict(len_surveyed=100, width=belt_transect_width_2m.id)

    invalid_data = dict(
        obs_belt_fishes=obs_belt_fishes_invalid, fishbelt_transect=fishbelt_transect
    )
    valid_data = dict(obs_belt_fishes=obs_belt_fishes_valid)

    validation = ObsFishBeltValidation(invalid_data)
    assert validation.validate_observation_count() == WARN

    validation = ObsFishBeltValidation(valid_data)
    assert validation.validate_observation_count() == OK

    invalid_low_biomass_data = dict(
        obs_belt_fishes=obs_belt_fishes_low_biomass_invalid,
        fishbelt_transect=fishbelt_transect,
    )

    validation = ObsFishBeltValidation(invalid_low_biomass_data)
    assert validation.validate_observation_density() == WARN

    invalid_high_biomass_data = dict(
        obs_belt_fishes=obs_belt_fishes_high_biomass_invalid,
        fishbelt_transect=fishbelt_transect,
    )

    validation = ObsFishBeltValidation(invalid_high_biomass_data)
    assert validation.validate_observation_density() == WARN

    valid_biomass_data = dict(
        obs_belt_fishes=obs_belt_fishes_biomass_valid,
        fishbelt_transect=fishbelt_transect,
    )
    validation = ObsFishBeltValidation(valid_biomass_data)
    assert validation.validate_observation_density() == OK

    validation = ObsFishBeltValidation(invalid_data)
    assert validation.validate_fish_count() == WARN

    validation = ObsFishBeltValidation(valid_data)
    assert validation.validate_fish_count() == OK


def test_obs_habitat_complexity_validation(habitat_complexity_score1):
    benthic_transect = {"len_surveyed": 100}
    obs_habitat_complexities_invalid = [
        {"interval": 1, "score": str(habitat_complexity_score1.id)},
        {"count": 2, "score": "INVALID SCORE ID"},
        {"count": 3, "score": str(habitat_complexity_score1.id)},
        {"count": 1, "score": str(habitat_complexity_score1.id)},
    ]

    obs_habitat_complexities_valid = [
        {"interval": 1, "score": str(habitat_complexity_score1.id)},
        {"interval": 2, "score": str(habitat_complexity_score1.id)},
        {"interval": 3, "score": str(habitat_complexity_score1.id)},
        {"interval": 1, "score": str(habitat_complexity_score1.id)},
        {"interval": 1, "score": str(habitat_complexity_score1.id)},
        {"interval": 1, "score": str(habitat_complexity_score1.id)},
        {"interval": 1, "score": str(habitat_complexity_score1.id)},
        {"interval": 1, "score": str(habitat_complexity_score1.id)},
        {"interval": 1, "score": str(habitat_complexity_score1.id)},
        {"interval": 1, "score": str(habitat_complexity_score1.id)},
    ]

    invalid_data = {
        "interval_size": 10,
        "obs_habitat_complexities": obs_habitat_complexities_invalid,
        "benthic_transect": benthic_transect,
    }

    valid_data = {
        "interval_size": 10,
        "obs_habitat_complexities": obs_habitat_complexities_valid,
        "benthic_transect": benthic_transect,
    }

    validation = ObsHabitatComplexitiesValidation(invalid_data)
    assert validation.validate_observation_count() == ERROR

    validation = ObsHabitatComplexitiesValidation(valid_data)
    assert validation.validate_observation_count() == OK

    validation = ObsHabitatComplexitiesValidation(invalid_data)
    assert validation.validate_scores() == ERROR

    validation = ObsHabitatComplexitiesValidation(valid_data)
    assert validation.validate_scores() == OK


def test_obs_benthic_lit_validation(all_test_benthic_attributes):
    benthic_transect = {"len_surveyed": 100}
    obs_benthic_lits = [{"length": 100}, {"length": 300}]

    invalid_len_data = {
        "benthic_transect": benthic_transect,
        "obs_benthic_lits": obs_benthic_lits,
    }

    obs_benthic_lits2 = [{"length": 9000}, {"length": 1000}]
    valid_data = {
        "benthic_transect": benthic_transect,
        "obs_benthic_lits": obs_benthic_lits2,
    }

    obs_benthic_lits3 = [
        {
            "attribute": BenthicAttribute.objects.get(name="Erythrastrea").id,
            "length": 9000,
        },
        {
            "attribute": BenthicAttribute.objects.get(name="Astreopora").id,
            "length": 1000,
        },
    ]

    invalid_hard_coral_data = {
        "benthic_transect": benthic_transect,
        "obs_benthic_lits": obs_benthic_lits3,
    }

    obs_benthic_lits4 = [
        {
            "attribute": BenthicAttribute.objects.get(name="Erythrastrea").id,
            "length": 9000,
        },
        {
            "attribute": BenthicAttribute.objects.get(name="Red Fleshy Algae").id,
            "length": 1000,
        },
    ]
    valid_hard_coral_data = {
        "benthic_transect": benthic_transect,
        "obs_benthic_lits": obs_benthic_lits4,
    }

    validation = ObsBenthicLITValidation(invalid_len_data)
    assert validation.validate() == WARN

    validation = ObsBenthicLITValidation(valid_data)
    assert validation.validate() == OK

    validation = ObsBenthicLITValidation(invalid_hard_coral_data)
    assert validation.validate() == WARN

    validation = ObsBenthicLITValidation(valid_hard_coral_data)
    assert validation.validate() == OK


def test_obs_benthic_percent_covered_validation():
    obs = [dict(percent_hard=0, percent_soft=20, percent_algae=12)]

    data = dict(obs_quadrat_benthic_percent=obs)

    invalid_obs = [dict(percent_hard=1, percent_soft=20, percent_algae=101)]
    invalid_data_gt_100_val = dict(obs_quadrat_benthic_percent=invalid_obs)

    invalid_obs = [dict(percent_hard=1, percent_soft=20, percent_algae=101)]
    invalid_data_lt_0 = dict(obs_quadrat_benthic_percent=invalid_obs)

    invalid_obs = [dict(percent_hard=1, percent_soft=20, percent_algae=None)]
    invalid_data_null = dict(obs_quadrat_benthic_percent=invalid_obs)

    invalid_obs = [dict(percent_hard=76, percent_soft=65, percent_algae=75)]
    invalid_data_gt_100_total = dict(obs_quadrat_benthic_percent=invalid_obs)

    validation = ObsBenthicPercentCoveredValidation(data)
    assert validation.validate_percent_values() == OK

    validation = ObsBenthicPercentCoveredValidation(invalid_data_null)
    assert validation.validate_percent_values() == ERROR

    validation = ObsBenthicPercentCoveredValidation(invalid_data_gt_100_val)
    assert validation.validate_percent_values() == ERROR

    validation = ObsBenthicPercentCoveredValidation(invalid_data_lt_0)
    assert validation.validate_percent_values() == ERROR

    validation = ObsBenthicPercentCoveredValidation(invalid_data_gt_100_total)
    assert validation.validate_percent_values() == ERROR

    data = dict(
        obs_quadrat_benthic_percent=[
            dict(percent_hard=1, percent_soft=20, percent_algae=10),
            dict(percent_hard=1, percent_soft=20, percent_algae=10),
            dict(percent_hard=1, percent_soft=20, percent_algae=10),
            dict(percent_hard=1, percent_soft=20, percent_algae=10),
            dict(percent_hard=1, percent_soft=20, percent_algae=10),
        ]
    )
    validation = ObsBenthicPercentCoveredValidation(data)
    assert validation.validate_quadrat_count() == OK

    invalid_data = dict(
        obs_quadrat_benthic_percent=[
            dict(percent_hard=1, percent_soft=20, percent_algae=10),
            dict(percent_hard=1, percent_soft=20, percent_algae=10),
        ]
    )
    validation = ObsBenthicPercentCoveredValidation(invalid_data)
    assert validation.validate_quadrat_count() == WARN


def test_obs_colonies_bleached_validation(
    benthic_attribute_3, growth_form1, growth_form2
):
    obs1 = [
        {
            "count_normal": 20,
            "count_pale": 50,
            "count_20": 10,
            "count_50": 30,
            "count_80": 20,
            "count_100": 50,
            "count_dead": 0,
            "attribute": str(benthic_attribute_3.id),
            "growth_form": str(growth_form1.id),
        }
    ]

    obs2 = [
        {
            "count_normal": 101,
            "count_pale": 100,
            "count_20": 100,
            "count_50": 100,
            "count_80": 100,
            "count_100": 100,
            "count_dead": 0,
            "attribute": str(benthic_attribute_3.id),
            "growth_form": str(growth_form2.id),
        }
    ]

    obs3 = [
        {
            "count_normal": 101,
            "count_pale": 100,
            "count_20": None,
            "count_50": 100,
            "count_80": "",
            "count_100": 0,
            "count_dead": 0,
            "attribute": str(benthic_attribute_3.id),
            "growth_form": str(growth_form2.id),
        }
    ]

    obs4 = obs1 + obs2
    obs5 = obs3 + obs2

    data = {"obs_colonies_bleached": obs1}
    data_gt_600 = {"obs_colonies_bleached": obs2}
    data_mix_non_numbers = {"obs_colonies_bleached": obs3}
    data_multi_obs = {"obs_colonies_bleached": obs4}
    data_multi_obs_duplicates = {"obs_colonies_bleached": obs5}

    validation = ObsColoniesBleachedValidation(data)
    assert validation.validate_colony_count() == OK

    validation = ObsColoniesBleachedValidation(data_mix_non_numbers)
    assert validation.validate_colony_count() == OK

    validation = ObsColoniesBleachedValidation(data_gt_600)
    assert validation.validate_colony_count() == WARN

    validation = ObsColoniesBleachedValidation(data_multi_obs)
    assert validation.validate_duplicate_genus_growth() == OK

    validation = ObsColoniesBleachedValidation(data_multi_obs_duplicates)
    assert validation.validate_duplicate_genus_growth() == ERROR
