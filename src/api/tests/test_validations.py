from api.models import BenthicAttribute, HabitatComplexityScore, Management, Site
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
from django.contrib.gis.geos import Point
from django.core.management import call_command
from django.test import TestCase

from .base_test_setup import BaseTestCase
from .data import TestDataMixin


class EmptyListValidationTest(TestCase):
    def test_validate_list(self):

        # OK
        validation = EmptyListValidation("abc", [1, 2, 3], "List is valid")
        self.assertEqual(OK, validation.validate())

        # Error: list is none
        validation = EmptyListValidation("abc", None, "List is None")
        self.assertEqual(ERROR, validation.validate())

        # Error: list is empty
        validation = EmptyListValidation("abc", [], "List is empty")
        self.assertEqual(ERROR, validation.validate())


class ValueInRangeValidationTest(TestCase):
    def test_validate_range(self):
        # OK
        validation = ValueInRangeValidation(
            identifier="abc", value=5, value_range=(0, 10)
        )
        self.assertEqual(OK, validation.validate())

        # OK
        validation = ValueInRangeValidation(
            identifier="abc", value=0, value_range=(0, 10)
        )
        self.assertEqual(OK, validation.validate())

        # ERROR
        validation = ValueInRangeValidation(
            identifier="abc",
            value=0,
            value_range=(0, 10),
            value_range_operators=("<=", ">"),
        )
        self.assertEqual(ERROR, validation.validate())

        # OK
        validation = ValueInRangeValidation(
            identifier="abc", value=10, value_range=(0, 10)
        )
        self.assertEqual(OK, validation.validate())

        # ERROR
        validation = ValueInRangeValidation(
            identifier="abc",
            value=10,
            value_range=(0, 10),
            value_range_operators=("<", ">="),
        )
        self.assertEqual(ERROR, validation.validate())

        # ERROR
        validation = ValueInRangeValidation(
            identifier="abc", value=11, value_range=(0, 10)
        )
        self.assertEqual(ERROR, validation.validate())


class SiteValidationTest(BaseTestCase):
    def test_status_ok(self):
        site_validation = SiteValidation(str(self.site1.pk))
        self.assertEqual(OK, site_validation.validate())

    def test_status_warning(self):
        site3 = Site.objects.create(
            project=self.project,
            name="site ab",
            location=Point(1, 1, srid=4326),
            country=self.country,
            reef_type=self.reef_type,
            exposure=self.reef_exposure,
            reef_zone=self.reef_zone,
        )

        site_validation = SiteValidation(str(self.site1.pk))
        logs = site_validation.logs
        self.assertEqual(WARN, site_validation.validate())
        self.assertTrue(logs["site"]["validate_similar"]["status"] == WARN)
        site3.delete()

    def test_status_error(self):

        # Invalid uuid test
        site_validation = SiteValidation(str("not-uuid"))
        self.assertEqual(ERROR, site_validation.validate())

        # Site doesn't exist test
        uuid = str("61bd9485-db2b-4e7d-8fe9-3c34b371ed0f")
        site_validation = SiteValidation(uuid)
        self.assertEqual(ERROR, site_validation.validate())

    def test_ignore_warning(self):
        site3 = Site.objects.create(
            project=self.project,
            name="site ab",
            location=Point(1, 1, srid=4326),
            country=self.country,
            reef_type=self.reef_type,
            exposure=self.reef_exposure,
            reef_zone=self.reef_zone,
        )

        site_validation = SiteValidation(str(self.site1.pk))
        site_validation.validate()
        site_validation.ignore_warning(SiteValidation.identifier, "validate_similar")

        retry_validation = SiteValidation(
            str(self.site1.pk), previous_validations=site_validation.logs["site"]
        )
        retry_validation.validate()
        retry_validation_logs = retry_validation.logs

        self.assertEqual(
            retry_validation_logs[SiteValidation.identifier]["validate_similar"][
                "status"
            ],
            IGNORE,
        )
        site3.delete()


# class ManagementValidationTest(BaseTestCase):
#     def test_status_ok(self):
#         management_validation = ManagementValidation(str(self.management.pk))
#         self.assertEqual(OK, management_validation.validate())

#     def test_status_warning(self):
#         mgmt2 = Management.objects.create(
#             project=self.project,
#             est_year=2000,
#             name="Test Management",
#             notes="Hey what is up",
#         )

#         management_validation = ManagementValidation(str(self.management.pk))
#         logs = management_validation.logs
#         self.assertEqual(WARN, management_validation.validate())
#         self.assertTrue(logs["management"]["validate_similar"]["status"] == WARN)
#         mgmt2.delete()

#     def test_status_error(self):

#         # Invalid uuid test
#         management_validation = ManagementValidation(str("not-uuid"))
#         self.assertEqual(ERROR, management_validation.validate())

#         # Management doesn't exist test
#         uuid = str("61bd9485-db2b-4e7d-8fe9-3c34b371ed0f")
#         management_validation = ManagementValidation(uuid)
#         self.assertEqual(ERROR, management_validation.validate())

#     def test_ignore_warning(self):
#         mgmt2 = Management.objects.create(
#             project=self.project,
#             est_year=2000,
#             name="Test Management",
#             notes="Hey what is up",
#         )

#         management_validation = ManagementValidation(str(self.management.pk))
#         management_validation.validate()
#         management_validation.ignore_warning(
#             ManagementValidation.identifier, "validate_similar"
#         )

#         retry_validation = ManagementValidation(
#             str(self.management.pk),
#             previous_validations=management_validation.logs[
#                 ManagementValidation.identifier
#             ],
#         )
#         retry_validation.validate()
#         retry_validation_logs = retry_validation.logs

#         self.assertEqual(
#             retry_validation_logs[ManagementValidation.identifier]["validate_similar"][
#                 "status"
#             ],
#             IGNORE,
#         )
#         mgmt2.delete()


class ObserverValidationTest(BaseTestCase):
    def test_status_error(self):
        # Observer doesn't exist test
        uuid = str("61bd9485-db2b-4e7d-8fe9-3c34b371ed00")
        observer_validation = ObserverValidation(uuid)
        self.assertEqual(ERROR, observer_validation.validate())


class ObsFishBeltValidationTest(BaseTestCase):
    def setUp(self):
        super(ObsFishBeltValidationTest, self).setUp()

        fishbelt_transect = dict(len_surveyed=100, width=self.belt_transect_width.id)
        obs_belt_fishes_invalid = [
            dict(count=1),
            dict(count=2),
            dict(count=3),
            dict(count=1),
        ]

        self.invalid_data = dict(
            obs_belt_fishes=obs_belt_fishes_invalid, fishbelt_transect=fishbelt_transect
        )
        fish_species_id = str(self.fish_species.id)
        obs_belt_fishes_low_biomass_invalid = [
            dict(
                count=24,
                fish_attribute=fish_species_id,
                size_bin=str(self.fish_size_bin.id),
                size=7.5,
            ),
            dict(
                count=32,
                fish_attribute=fish_species_id,
                size_bin=str(self.fish_size_bin.id),
                size=7.5,
            ),
            dict(
                count=44,
                fish_attribute=fish_species_id,
                size_bin=str(self.fish_size_bin.id),
                size=7.5,
            ),
            dict(
                count=1,
                fish_attribute=fish_species_id,
                size_bin=str(self.fish_size_bin.id),
                size=7.5,
            ),
            dict(
                count=3,
                fish_attribute=fish_species_id,
                size_bin=str(self.fish_size_bin.id),
                size=7.5,
            ),
        ]

        self.invalid_low_biomass_data = dict(
            obs_belt_fishes=obs_belt_fishes_low_biomass_invalid,
            fishbelt_transect=fishbelt_transect,
        )

        obs_belt_fishes_high_biomass_invalid = [
            dict(
                count=2403,
                fish_attribute=fish_species_id,
                size_bin=str(self.fish_size_bin.id),
                size=7.5,
            ),
            dict(
                count=3200,
                fish_attribute=fish_species_id,
                size_bin=str(self.fish_size_bin.id),
                size=7.5,
            ),
            dict(
                count=445,
                fish_attribute=fish_species_id,
                size_bin=str(self.fish_size_bin.id),
                size=7.5,
            ),
            dict(
                count=1100,
                fish_attribute=fish_species_id,
                size_bin=str(self.fish_size_bin.id),
                size=7.5,
            ),
            dict(
                count=3000,
                fish_attribute=fish_species_id,
                size_bin=str(self.fish_size_bin.id),
                size=7.5,
            ),
        ]

        self.invalid_high_biomass_data = dict(
            obs_belt_fishes=obs_belt_fishes_high_biomass_invalid,
            fishbelt_transect=fishbelt_transect,
        )

        obs_belt_fishes_biomass_valid = [
            dict(
                count=2403,
                fish_attribute=fish_species_id,
                size_bin=str(self.fish_size_bin.id),
                size=7.5,
            ),
            dict(
                count=32,
                fish_attribute=fish_species_id,
                size_bin=str(self.fish_size_bin.id),
                size=7.5,
            ),
            dict(
                count=445,
                fish_attribute=fish_species_id,
                size_bin=str(self.fish_size_bin.id),
                size=7.5,
            ),
            dict(
                count=1100,
                fish_attribute=fish_species_id,
                size_bin=str(self.fish_size_bin.id),
                size=7.5,
            ),
            dict(
                count=3000,
                fish_attribute=fish_species_id,
                size_bin=str(self.fish_size_bin.id),
                size=7.5,
            ),
        ]

        self.valid_biomass_data = dict(
            obs_belt_fishes=obs_belt_fishes_biomass_valid,
            fishbelt_transect=fishbelt_transect,
        )

        obs_belt_fishes_valid = [
            dict(count=1),
            dict(count=2),
            dict(count=3),
            dict(count=1),
            dict(count=10),
        ]

        self.valid_data = dict(obs_belt_fishes=obs_belt_fishes_valid)

    def tearDown(self):
        super(ObsFishBeltValidationTest, self).tearDown()
        self.invalid_data = None
        self.valid_data = None
        self.invalid_low_biomass_data = None
        self.invalid_high_biomass_data = None

    def test_validate_observation_count(self):
        validation = ObsFishBeltValidation(self.invalid_data)
        self.assertEqual(WARN, validation.validate_observation_count())

        validation = ObsFishBeltValidation(self.valid_data)
        self.assertEqual(OK, validation.validate_observation_count())

    def test_validate_observation_density(self):
        validation = ObsFishBeltValidation(self.invalid_low_biomass_data)
        self.assertEqual(WARN, validation.validate_observation_density())

        validation = ObsFishBeltValidation(self.invalid_high_biomass_data)
        self.assertEqual(WARN, validation.validate_observation_density())

        validation = ObsFishBeltValidation(self.valid_biomass_data)
        self.assertEqual(OK, validation.validate_observation_density())

    def test_validate_fish_count(self):
        validation = ObsFishBeltValidation(self.invalid_data)
        self.assertEqual(WARN, validation.validate_fish_count())

        validation = ObsFishBeltValidation(self.valid_data)
        self.assertEqual(OK, validation.validate_fish_count())


class ObsHabitatComplexitiesValidationTest(BaseTestCase):
    def setUp(self):
        super(ObsHabitatComplexitiesValidationTest, self).setUp()
        benthic_transect = dict(len_surveyed=100)
        score = HabitatComplexityScore.objects.create(name="test", val=1)
        obs_habitat_complexities_invalid = [
            dict(interval=1, score=str(score.id)),
            dict(count=2, score="INVALID SCORE ID"),
            dict(count=3, score=str(score.id)),
            dict(count=1, score=str(score.id)),
        ]

        self.invalid_data = dict(
            interval_size=10,
            obs_habitat_complexities=obs_habitat_complexities_invalid,
            benthic_transect=benthic_transect,
        )

        obs_habitat_complexities_valid = [
            dict(interval=1, score=str(score.id)),
            dict(interval=2, score=str(score.id)),
            dict(interval=3, score=str(score.id)),
            dict(interval=1, score=str(score.id)),
            dict(interval=1, score=str(score.id)),
            dict(interval=1, score=str(score.id)),
            dict(interval=1, score=str(score.id)),
            dict(interval=1, score=str(score.id)),
            dict(interval=1, score=str(score.id)),
            dict(interval=1, score=str(score.id)),
        ]

        self.valid_data = dict(
            interval_size=10,
            obs_habitat_complexities=obs_habitat_complexities_valid,
            benthic_transect=benthic_transect,
        )

    def tearDown(self):
        super(ObsHabitatComplexitiesValidationTest, self).tearDown()
        self.valid_data = None
        self.invalid_data = None

    def test_validate_observation_count(self):
        validation = ObsHabitatComplexitiesValidation(self.invalid_data)
        self.assertEqual(ERROR, validation.validate_observation_count())

        validation = ObsHabitatComplexitiesValidation(self.valid_data)
        self.assertEqual(OK, validation.validate_observation_count())

    def test_validate_scores(self):
        validation = ObsHabitatComplexitiesValidation(self.invalid_data)
        self.assertEqual(ERROR, validation.validate_scores())

        validation = ObsHabitatComplexitiesValidation(self.valid_data)
        self.assertEqual(OK, validation.validate_scores())


class ObsBenthicLITValidationTest(BaseTestCase, TestDataMixin):
    def setUp(self):
        super(ObsBenthicLITValidationTest, self).setUp()
        self.load_benthicattributes()

        # call_command("refresh_benthic")

        benthic_transect = dict(len_surveyed=100)
        obs_benthic_lits = [{"length": 100}, {"length": 300}]

        self.invalid_len_data = dict(
            benthic_transect=benthic_transect, obs_benthic_lits=obs_benthic_lits
        )

        obs_benthic_lits2 = [{"length": 9000}, {"length": 1000}]
        self.valid_data = dict(
            benthic_transect=benthic_transect, obs_benthic_lits=obs_benthic_lits2
        )

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
        self.invalid_hard_coral_data = dict(
            benthic_transect=benthic_transect, obs_benthic_lits=obs_benthic_lits3
        )
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
        self.valid_hard_coral_data = dict(
            benthic_transect=benthic_transect, obs_benthic_lits=obs_benthic_lits4
        )

    def tearDown(self):
        super(ObsBenthicLITValidationTest, self).tearDown()
        self.unload_benthicattributes()
        self.valid_data = None
        self.invalid_len_data = None
        self.valid_hard_coral_data = None
        self.invalid_hard_coral_data = None

    def test_validate_total_length(self):
        validation = ObsBenthicLITValidation(self.invalid_len_data)
        self.assertEqual(WARN, validation.validate())

        validation = ObsBenthicLITValidation(self.valid_data)
        self.assertEqual(OK, validation.validate())

    def test_validate_hard_coral(self):
        validation = ObsBenthicLITValidation(self.invalid_hard_coral_data)
        self.assertEqual(WARN, validation.validate())

        validation = ObsBenthicLITValidation(self.valid_hard_coral_data)
        self.assertEqual(OK, validation.validate())


class BenthicTransectValidationTest(BaseTestCase):
    def setUp(self):
        super(BenthicTransectValidationTest, self).setUp()

        sample_event = dict(
            relative_depth=str(self.relative_depth.id), site=str(self.site1.id)
        )
        benthic_transect = dict(number=1)
        self.invalid_data = dict(
            protocol="benthicpit",
            sample_event=sample_event,
            benthic_transect=benthic_transect,
        )

        sample_event_2 = dict(relative_depth="")
        benthic_transect = dict(number=1)
        self.invalid_data_missing_id = dict(
            sample_event=sample_event_2, benthic_transect=benthic_transect
        )

        benthic_transect2 = dict(number=2)
        self.valid_data = dict(
            sample_event=sample_event, benthic_transect=benthic_transect2
        )

        sample_event = dict(
            relative_depth=str(self.relative_depth.id), site=str(self.site1.id)
        )
        benthic_transect = dict(number=1)
        self.valid_data_diff_trans_method = dict(
            protocol="benthiclit",
            sample_event=sample_event,
            benthic_transect=benthic_transect,
        )

    def tearDown(self):
        super(BenthicTransectValidationTest, self).tearDown()
        self.invalid_data = None
        self.valid_data = None

    def test_validate_duplicate(self):
        validation = BenthicTransectValidation(self.invalid_data)
        self.assertEqual(WARN, validation.validate_duplicate())

        validation = BenthicTransectValidation(self.invalid_data_missing_id)
        self.assertEqual(ERROR, validation.validate_duplicate())

        validation = BenthicTransectValidation(self.valid_data)
        self.assertEqual(OK, validation.validate_duplicate())

        validation = BenthicTransectValidation(self.valid_data_diff_trans_method)
        self.assertEqual(OK, validation.validate_duplicate())


class ObservationsValidationTest(BaseTestCase):
    def setUp(self):
        super(ObservationsValidationTest, self).setUp()
        observations = [
            dict(interval=1, score="test1"),
            dict(interval=2, score="test2"),
            dict(interval=3, score="test3"),
        ]
        self.data = dict(obs_habitat_complexities=observations)

        observations_invalid = [
            dict(interval=1, score="test1"),
            dict(interval=1, score="test1"),
            dict(interval=1, score="test1"),
        ]
        self.invalid_data = dict(obs_habitat_complexities=observations_invalid)

    def tearDown(self):
        super(ObservationsValidationTest, self).tearDown()
        self.data = None
        self.invalid_data = None

    def test_validate_all_equal(self):
        validation = ObservationsValidation(self.data)
        self.assertEqual(OK, validation.validate_all_equal())

        validation = ObservationsValidation(self.invalid_data)
        self.assertEqual(WARN, validation.validate_all_equal())


class ObsBenthicPercentCoveredValidationTest(BaseTestCase):
    def setUp(self):
        super(ObsBenthicPercentCoveredValidationTest, self).setUp()

        obs = [dict(percent_hard=0, percent_soft=20, percent_algae=12)]

        self.data = dict(obs_quadrat_benthic_percent=obs)

        invalid_obs = [dict(percent_hard=1, percent_soft=20, percent_algae=101)]
        self.invalid_data_gt_100_val = dict(obs_quadrat_benthic_percent=invalid_obs)

        invalid_obs = [dict(percent_hard=1, percent_soft=20, percent_algae=101)]
        self.invalid_data_lt_0 = dict(obs_quadrat_benthic_percent=invalid_obs)

        invalid_obs = [dict(percent_hard=1, percent_soft=20, percent_algae=None)]
        self.invalid_data_null = dict(obs_quadrat_benthic_percent=invalid_obs)

        invalid_obs = [dict(percent_hard=76, percent_soft=65, percent_algae=75)]
        self.invalid_data_gt_100_total = dict(obs_quadrat_benthic_percent=invalid_obs)

    def tearDown(self):
        super(ObsBenthicPercentCoveredValidationTest, self).tearDown()

        self.data = None
        self.invalid_data_gt_100_val = None
        self.invalid_data_lt_0 = None
        self.invalid_data_null = None

    def test_validate_percent_values(self):
        validation = ObsBenthicPercentCoveredValidation(self.data)
        self.assertEqual(OK, validation.validate_percent_values())

        validation = ObsBenthicPercentCoveredValidation(self.invalid_data_null)
        self.assertEqual(OK, validation.validate_percent_values())

        validation = ObsBenthicPercentCoveredValidation(self.invalid_data_gt_100_val)
        self.assertEqual(ERROR, validation.validate_percent_values())

        validation = ObsBenthicPercentCoveredValidation(self.invalid_data_lt_0)
        self.assertEqual(ERROR, validation.validate_percent_values())

        validation = ObsBenthicPercentCoveredValidation(self.invalid_data_gt_100_total)
        self.assertEqual(ERROR, validation.validate_percent_values())

    def test_validate_quadrat_count(self):
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
        self.assertEqual(OK, validation.validate_quadrat_count())

        invalid_data = dict(
            obs_quadrat_benthic_percent=[
                dict(percent_hard=1, percent_soft=20, percent_algae=10),
                dict(percent_hard=1, percent_soft=20, percent_algae=10),
            ]
        )
        validation = ObsBenthicPercentCoveredValidation(invalid_data)
        self.assertEqual(WARN, validation.validate_quadrat_count())


class ObsColoniesBleachedValidationTest(BaseTestCase):
    def _create_obs(
        self,
        normal=0,
        pale=0,
        bleach_20=0,
        bleach_50=0,
        bleach_80=0,
        bleach_100=0,
        dead=0,
        attribute=None,
        growth_form=None,
    ):
        return [
            dict(
                count_normal=normal,
                count_pale=pale,
                count_20=bleach_20,
                count_50=bleach_50,
                count_80=bleach_80,
                count_100=bleach_100,
                count_dead=dead,
                attribute=attribute,
                growth_form=growth_form,
            )
        ]

    def setUp(self):
        super(ObsColoniesBleachedValidationTest, self).setUp()

        obs1 = self._create_obs(20, 50, 10, 30, 20, 50, "Coelastrea", "Branching")
        self.data = dict(obs_colonies_bleached=obs1)

        obs2 = self._create_obs(
            101, 100, 100, 100, 100, 100, "Coelastrea", "Encrusting"
        )
        self.data_gt_600 = dict(obs_colonies_bleached=obs2)

        obs3 = self._create_obs(
            101, 100, None, 100, 100, "", "Coelastrea", "Encrusting"
        )
        self.data_mix_non_numbers = dict(obs_colonies_bleached=obs3)

        obs4 = obs1 + obs2
        self.data_multi_obs = dict(obs_colonies_bleached=obs4)

        obs5 = obs3 + obs2
        self.data_multi_obs_duplicates = dict(obs_colonies_bleached=obs5)

    def tearDown(self):
        super(ObsColoniesBleachedValidationTest, self).tearDown()
        self.data = None
        self.data_gt_600 = None

    def test_validate_colony_count(self):
        validation = ObsColoniesBleachedValidation(self.data)
        self.assertEqual(OK, validation.validate_colony_count())

        validation = ObsColoniesBleachedValidation(self.data_mix_non_numbers)
        self.assertEqual(OK, validation.validate_colony_count())

        validation = ObsColoniesBleachedValidation(self.data_gt_600)
        self.assertEqual(WARN, validation.validate_colony_count())

    def test_validate_duplicate_genus_growth(self):
        validation = ObsColoniesBleachedValidation(self.data_multi_obs)
        self.assertEqual(OK, validation.validate_duplicate_genus_growth())

        validation = ObsColoniesBleachedValidation(self.data_multi_obs_duplicates)
        self.assertEqual(ERROR, validation.validate_duplicate_genus_growth())
