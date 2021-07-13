import datetime

from django.contrib.gis.geos import Point

import pytest

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
    validation = ValueInRangeValidation(
        identifier="abc", value=5, value_range=(0, 10)
    )
    assert validation.validate() == OK

    # OK
    validation = ValueInRangeValidation(
        identifier="abc", value=0, value_range=(0, 10)
    )
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
    validation = ValueInRangeValidation(
        identifier="abc", value=10, value_range=(0, 10)
    )
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
    validation = ValueInRangeValidation(
        identifier="abc", value=11, value_range=(0, 10)
    )
    assert validation.validate() == ERROR


def test_site_validation(db_setup, site1, project1, country1, reef_type1, reef_exposure1, reef_zone1):
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

        assert retry_validation_logs[SiteValidation.identifier]["validate_similar"]["status"] == IGNORE
    finally:
        if site3:
            site3.delete()


def test_management_validation(db_setup, management1, project1, site1):
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
            site=site1, management=mgmt2, sample_date=datetime.date(2018, 7, 13),
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

        assert retry_validation_logs[ManagementValidation.identifier]["validate_similar"][
            "status"
        ] == IGNORE

    finally:
        if benthic_transect:
            benthic_transect.delete()
        if mgmt2:
            mgmt2.delete()


def test_observer_validation(db_setup):
    # Observer doesn't exist test
    uuid = str("61bd9485-db2b-4e7d-8fe9-3c34b371ed00")
    validation = ObserverValidation(uuid)
    validation.validate() == ERROR


def test_obs_fish_belt_validation(
    db_setup,
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



# TODO: port src/api/tests/test_validations.py to here