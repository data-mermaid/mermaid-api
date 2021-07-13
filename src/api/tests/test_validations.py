import datetime

from django.contrib.gis.geos import Point
from django.test import TestCase

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
from .base_test_setup import BaseTestCase
from .data import TestDataMixin


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
            site=str(self.site1.id),
            management=str(self.management.id),
            sample_date=datetime.date(2018, 7, 13),
            depth=1.1,
            relative_depth=str(self.relative_depth.id),
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
        self.assertEqual(ERROR, validation.validate_percent_values())

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
