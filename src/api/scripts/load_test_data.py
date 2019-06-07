from api.models.base import AuthUser
from api.models.base import Profile
from api.models.mermaid import (
    ReefExposure,
    Country,
    ReefType,
    ReefZone,
    Site,
    ProjectProfile,
    Project,
    Management,
    ManagementParty,
)


class TestDataGenerator(object):

    def create(self):
        self._create_projects()
        self._create_profiles()
        self._create_project_profiles()
        self._create_sites()
        self._create_managements()

    def _create_projects(self):
        self.project_1, _ = Project.objects.get_or_create(name='Project 1')
        self.project_2, _ = Project.objects.get_or_create(name='Project 2')
        self.project_3, _ = Project.objects.get_or_create(name='Project 3')

    def _create_profiles(self):

        self.dustin_profile, _ = Profile.objects.get_or_create(
            email='dustin@sparkgeo.com',
            first_name='Dustin',
            last_name='Sampson'
        )
        self.dustin_auth_user, _ = AuthUser.objects.get_or_create(
            profile=self.dustin_profile,
            user_id='google-oauth2|101094059240252871633'
        )

        self.kim_profile, _ = Profile.objects.get_or_create(
            email='kfisher@wcs.org',
            first_name='Kim',
            last_name='Fisher'
        )
        self.kim_auth_user, _ = AuthUser.objects.get_or_create(
            profile=self.kim_profile,
            user_id='google-oauth2|116024188080902845538'
        )

        self.emily_profile, _ = Profile.objects.get_or_create(
            email='edarling@wcs.org',
            first_name='Emily',
            last_name='Darling'
        )
        self.emily_auth_user, _ = AuthUser.objects.get_or_create(
            profile=self.emily_profile,
            user_id='google-oauth2|107520280668817898296'
        )

    def _create_project_profiles(self):
        # Project 1
        ProjectProfile.objects.get_or_create(
            project=self.project_1,
            profile=self.dustin_profile,
            role=ProjectProfile.ADMIN
        )
        ProjectProfile.objects.get_or_create(
            project=self.project_1,
            profile=self.kim_profile,
            role=ProjectProfile.COLLECTOR
        )
        ProjectProfile.objects.get_or_create(
            project=self.project_1,
            profile=self.emily_profile,
            role=ProjectProfile.COLLECTOR
        )

        # Project 2
        ProjectProfile.objects.get_or_create(
            project=self.project_2,
            profile=self.dustin_profile,
            role=ProjectProfile.COLLECTOR
        )
        ProjectProfile.objects.get_or_create(
            project=self.project_2,
            profile=self.kim_profile,
            role=ProjectProfile.ADMIN
        )
        ProjectProfile.objects.get_or_create(
            project=self.project_2,
            profile=self.emily_profile,
            role=ProjectProfile.COLLECTOR
        )

        # Project 3
        ProjectProfile.objects.get_or_create(
            project=self.project_3,
            profile=self.dustin_profile,
            role=ProjectProfile.COLLECTOR
        )
        ProjectProfile.objects.get_or_create(
            project=self.project_3,
            profile=self.kim_profile,
            role=ProjectProfile.COLLECTOR
        )
        ProjectProfile.objects.get_or_create(
            project=self.project_3,
            profile=self.emily_profile,
            role=ProjectProfile.ADMIN
        )

    def _create_sites(self):
        country_1 = Country.objects.first()
        country_2 = Country.objects.last()

        reef_type_1 = ReefType.objects.first()
        reef_type_2 = ReefType.objects.last()

        reef_zone_1 = ReefZone.objects.first()
        reef_zone_2 = ReefZone.objects.last()

        exposure_1 = ReefExposure.objects.first()
        exposure_2 = ReefExposure.objects.last()

        self.site_1a = Site.objects.get_or_create(
            project=self.project_1,
            name='Site 1a',
            country=country_1,
            reef_type=reef_type_1,
            reef_zone=reef_zone_1,
            exposure=exposure_1,
            location='SRID=4326;POINT(-130 50)'
        )

        self.site_1b = Site.objects.get_or_create(
            project=self.project_1,
            name='Site 1b',
            country=country_2,
            reef_type=reef_type_2,
            reef_zone=reef_zone_1,
            exposure=exposure_2,
            location='SRID=4326;POINT(-111 33)'
        )

        self.site_2 = Site.objects.get_or_create(
            project=self.project_2,
            name='Site 2',
            country=country_2,
            reef_type=reef_type_2,
            reef_zone=reef_zone_2,
            exposure=exposure_2,
            location='SRID=4326;POINT(110 -21)'
        )

        self.site_3 = Site.objects.get_or_create(
            project=self.project_3,
            name='Site 3',
            country=country_1,
            reef_type=reef_type_2,
            reef_zone=reef_zone_1,
            exposure=exposure_2,
            location='SRID=4326;POINT(132 15)'
        )

    def _create_managements(self):
        management_party_1 = ManagementParty.objects.first()
        management_party_2 = ManagementParty.objects.last()

        self.management_1a, _ = Management.objects.get_or_create(
            project=self.project_1,
            name='MR-1a: Project 1',
            est_year='2011',
            size=200,
            size_limits=True,
            gear_restriction=True
        )

        self.management_1a.parties.add(management_party_1)
        self.management_1a.save()

        self.management_1b, _ = Management.objects.get_or_create(
            project=self.project_1,
            name='MR-1b: Project 1',
            est_year='2012',
            size=122,
            no_take=True,
            periodic_closure=True
        )
        self.management_1b.parties.add(management_party_1)
        self.management_1b.parties.add(management_party_2)
        self.management_1b.save()

        self.management_2, _ = Management.objects.get_or_create(
            project=self.project_2,
            name='MR-2: Project 2',
            est_year='2011',
            size=51
        )
        self.management_2.parties.add(management_party_1)
        self.management_2.save()

        self.management_3, _ = Management.objects.get_or_create(
            project=self.project_2,
            name='MR-3: Project 3',
            est_year='1999',
            size=13,
            size_limits=True,
            gear_restriction=True,
            species_restriction=True
        )
        self.management_3.parties.add(management_party_1)
        self.management_3.parties.add(management_party_2)
        self.management_3.save()


def run():
    test_data_gen = TestDataGenerator()
    test_data_gen.create()
