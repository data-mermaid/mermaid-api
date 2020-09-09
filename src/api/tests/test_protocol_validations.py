import copy

from django.test import TestCase

from api.models.mermaid import CollectRecord
from api.submission.protocol_validations import (
    BenthicLITProtocolValidation,
    BenthicPITProtocolValidation,
    FishBeltProtocolValidation,
    HabitatComplexityProtocolValidation,
)
from api.submission.validations import ERROR, OK, WARN
from .data import MockRequest, TestDataMixin


class FishBeltProtocolValidationTest(TestCase, TestDataMixin):
    def setUp(self):
        self.load_projects()
        self.load_project_profiles()
        self.load_sample_events()
        self.load_fishattributes()

        observations = [
            dict(
                count=10,
                fish_attribute=str(self.fish_species1.id),
                size_bin=str(self.fish_size_bin1.id),
                size=17.5,
            ),
            dict(
                count=15,
                fish_attribute=str(self.fish_species1.id),
                size_bin=str(self.fish_size_bin1.id),
                size=17.5,
            ),
            dict(
                count=20,
                fish_attribute=str(self.fish_species1.id),
                size_bin=str(self.fish_size_bin1.id),
                size=17.5,
            ),
            dict(
                count=30,
                fish_attribute=str(self.fish_species1.id),
                size_bin=str(self.fish_size_bin1.id),
                size=17.5,
            ),
            dict(
                count=35,
                fish_attribute=str(self.fish_species1.id),
                size_bin=str(self.fish_size_bin1.id),
                size=17.5,
            ),
            dict(
                count=40,
                fish_attribute=str(self.fish_species1.id),
                size_bin=str(self.fish_size_bin1.id),
                size=17.5,
            ),
        ]
        data_ok = dict(
            protocol="fishbelt",
            obs_belt_fishes=observations,
            fishbelt_transect=dict(
                width=str(self.belt_transect_width2.id),
                number=1,
                len_surveyed=100,
                depth=1,
            ),
            sample_event=dict(
                management=str(self.sample_event1.management.id),
                site=str(self.sample_event1.site.id),
                sample_date=str(self.sample_event1.sample_date),
            ),
            observers=[{"profile": str(self.project1_admin.profile.id)}],
        )
        self.collect_record_ok = CollectRecord.objects.create(
            project=self.project1,
            profile=self.profile1,
            stage=CollectRecord.VALIDATED_STAGE,
            data=data_ok,
        )

        observations_warn = copy.deepcopy(observations)
        data_warn = copy.deepcopy(data_ok)
        observations_warn.pop()
        observations_warn.pop()
        observations_warn.pop()

        data_warn["obs_belt_fishes"] = observations_warn
        data_warn["sample_event"]["depth"] = 50.0
        data_warn["fishbelt_transect"]["len_surveyed"] = 101
        data_warn["fishbelt_transect"]["depth"] = 31
        self.collect_record_warn = CollectRecord.objects.create(
            project=self.project1,
            profile=self.profile1,
            stage=CollectRecord.VALIDATED_STAGE,
            data=data_warn,
        )

        data_error = copy.deepcopy(data_ok)
        data_error["observers"] = None
        self.collect_record_error = CollectRecord.objects.create(
            project=self.project1,
            profile=self.profile1,
            stage=CollectRecord.VALIDATED_STAGE,
            data=data_error,
        )
        self.request = MockRequest(token=self.profile1_token)

    def tearDown(self):
        self.unload_sample_events()
        self.unload_project_profiles()
        self.unload_projects()
        self.unload_fishattributes()

        self.collect_record_ok.delete()
        self.collect_record_warn.delete()
        self.collect_record_error.delete()

        self.collect_record_ok = None
        self.collect_record_warn = None
        self.collect_record_error = None
        self.request = None

    def test_validate_ok(self):
        validation = FishBeltProtocolValidation(
            self.collect_record_ok, request=self.request
        )
        results = validation.validate()
        self.assertEqual(OK, results)

    def test_validate_warn(self):
        validation = FishBeltProtocolValidation(
            self.collect_record_warn, request=self.request
        )
        result = validation.validate()
        self.assertEqual(WARN, result)
        self.assertEqual(
            WARN, validation.validations["len_surveyed"]["validate_range"]["status"]
        )
        self.assertEqual(
            WARN,
            validation.validations["obs_belt_fishes"]["validate_observation_density"][
                "status"
            ],
        )
        self.assertEqual(
            WARN,
            validation.validations["obs_belt_fishes"]["validate_observation_count"][
                "status"
            ],
        )
        self.assertEqual(
            WARN, validation.validations["depth"]["validate_range"]["status"]
        )

    def test_validate_error(self):
        validation = FishBeltProtocolValidation(
            self.collect_record_error, request=self.request
        )
        self.assertEqual(ERROR, validation.validate())


class BenthicPITProtocolValidationTest(TestCase, TestDataMixin):
    def setUp(self):
        self.load_projects()
        self.load_project_profiles()
        self.load_sample_events()
        self.load_benthicattributes()

        observations = [
            dict(attribute=str(self.benthic_attribute1a.id), interval=5),
            dict(attribute=str(self.benthic_attribute1a.id), interval=10),
            dict(attribute=str(self.benthic_attribute1a.id), interval=15),
            dict(attribute=str(self.benthic_attribute1a.id), interval=20),
            dict(attribute=str(self.benthic_attribute1a.id), interval=25),
            dict(attribute=str(self.benthic_attribute2c.id), interval=30),
        ]
        data_ok = dict(
            protocol="benthicpit",
            obs_benthic_pits=observations,
            benthic_transect=dict(depth=1, number=1, len_surveyed=30),
            interval_size=5,
            interval_start=5,
            sample_event=dict(
                management=str(self.sample_event1.management.id),
                site=str(self.sample_event1.site.id),
                sample_date=str(self.sample_event1.sample_date),
            ),
            observers=[{"profile": str(self.project1_admin.profile.id)}],
        )
        self.collect_record_ok = CollectRecord.objects.create(
            project=self.project1,
            profile=self.profile1,
            stage=CollectRecord.VALIDATED_STAGE,
            data=data_ok,
        )

        data_error = copy.deepcopy(data_ok)
        data_error["obs_benthic_pits"] = observations[0:3]
        self.collect_record_error = CollectRecord.objects.create(
            project=self.project1,
            profile=self.profile1,
            stage=CollectRecord.VALIDATED_STAGE,
            data=data_error,
        )
        self.request = MockRequest(token=self.profile1_token)

    def tearDown(self):
        self.unload_sample_events()
        self.unload_project_profiles()
        self.unload_projects()

        self.unload_benthicattributes()

        self.collect_record_ok.delete()
        self.collect_record_error.delete()

        self.collect_record_ok = None
        self.collect_record_error = None
        self.request = None

    def test_validate_ok(self):
        validation = BenthicPITProtocolValidation(
            self.collect_record_ok, request=self.request
        )
        result = validation.validate()
        self.assertEqual(OK, result)

    def test_validate_error(self):
        validation = BenthicPITProtocolValidation(
            self.collect_record_error, request=self.request
        )
        self.assertEqual(ERROR, validation.validate())
        self.assertEqual(
            ERROR,
            validation.validations["obs_benthic_pits"]["validate_observation_count"][
                "status"
            ],
        )


class BenthicLITProtocolValidationTest(TestCase, TestDataMixin):
    def setUp(self):
        self.load_sample_events()
        self.load_project_profiles()
        self.load_projects()
        self.load_benthicattributes()

        observations = [
            dict(attribute=str(self.benthic_attribute1a.id), length=1000),
            dict(attribute=str(self.benthic_attribute1a.id), length=1500),
            dict(attribute=str(self.benthic_attribute1a.id), length=2000),
            dict(attribute=str(self.benthic_attribute1a.id), length=2500),
            dict(attribute=str(self.benthic_attribute2c.id), length=3000),
        ]
        data_ok = dict(
            protocol="benthiclit",
            obs_benthic_lits=observations,
            benthic_transect=dict(depth=1, number=2, len_surveyed=100),
            sample_event=dict(
                management=str(self.sample_event1.management.id),
                site=str(self.sample_event1.site.id),
                sample_date=str(self.sample_event1.sample_date),
            ),
            observers=[{"profile": str(self.project1_admin.profile.id)}],
        )
        self.collect_record_ok = CollectRecord.objects.create(
            project=self.project1,
            profile=self.profile1,
            stage=CollectRecord.VALIDATED_STAGE,
            data=data_ok,
        )

        data_error = copy.deepcopy(data_ok)
        data_error["obs_benthic_lits"] = observations[0:3]
        self.collect_record_error = CollectRecord.objects.create(
            project=self.project1,
            profile=self.profile1,
            stage=CollectRecord.VALIDATED_STAGE,
            data=data_error,
        )
        self.request = MockRequest(token=self.profile1_token)

    def tearDown(self):
        self.unload_sample_events()
        self.unload_project_profiles()
        self.unload_projects()
        self.unload_benthicattributes()

        self.collect_record_ok.delete()
        self.collect_record_error.delete()

        self.collect_record_ok = None
        self.collect_record_error = None
        self.request = None

    def test_validate_ok(self):
        validation = BenthicLITProtocolValidation(
            self.collect_record_ok, request=self.request
        )
        result = validation.validate()
        self.assertEqual(OK, result)

    def test_validate_warning(self):
        validation = BenthicLITProtocolValidation(
            self.collect_record_error, request=self.request
        )
        self.assertEqual(WARN, validation.validate())
        self.assertEqual(
            WARN,
            validation.validations["obs_benthic_lits"]["validate_total_length"][
                "status"
            ],
        )


class HabitatComplexityProtocolValidationTest(TestCase, TestDataMixin):
    def setUp(self):
        self.load_projects()
        self.load_project_profiles()
        self.load_sample_events()

        observations = [
            dict(score=str(self.habitat_complexity_score1.id), interval=0),
            dict(score=str(self.habitat_complexity_score1.id), interval=5),
            dict(score=str(self.habitat_complexity_score1.id), interval=10),
            dict(score=str(self.habitat_complexity_score1.id), interval=15),
            dict(score=str(self.habitat_complexity_score1.id), interval=20),
            dict(score=str(self.habitat_complexity_score1.id), interval=25),
        ]
        data_ok = dict(
            protocol="habitatcomplexity",
            obs_habitat_complexities=observations,
            benthic_transect=dict(depth=1, number=2, len_surveyed=30),
            interval_size=5,
            sample_event=dict(
                management=str(self.sample_event1.management.id),
                site=str(self.sample_event1.site.id),
                sample_date=str(self.sample_event1.sample_date),
            ),
            observers=[{"profile": str(self.project1_admin.profile.id)}],
        )
        self.collect_record_ok = CollectRecord.objects.create(
            project=self.project1,
            profile=self.profile1,
            stage=CollectRecord.VALIDATED_STAGE,
            data=data_ok,
        )

        data_error = copy.deepcopy(data_ok)
        data_error["obs_habitat_complexities"][0]["score"] = "invalid score id"
        self.collect_record_error = CollectRecord.objects.create(
            project=self.project1,
            profile=self.profile1,
            stage=CollectRecord.VALIDATED_STAGE,
            data=data_error,
        )

        self.request = MockRequest(token=self.profile1_token)

    def tearDown(self):
        self.unload_sample_events()
        self.unload_project_profiles()
        self.unload_projects()

        self.collect_record_ok.delete()
        self.collect_record_error.delete()

        self.collect_record_ok = None
        self.collect_record_error = None
        self.request = None

    def test_validate_ok(self):
        validation = HabitatComplexityProtocolValidation(
            self.collect_record_ok, request=self.request
        )
        self.assertEqual(OK, validation.validate())

    def test_validate_error(self):
        validation = HabitatComplexityProtocolValidation(
            self.collect_record_error, request=self.request
        )
        self.assertEqual(ERROR, validation.validate())
        self.assertEqual(
            ERROR,
            validation.validations["obs_habitat_complexities"]["validate_scores"][
                "status"
            ],
        )
