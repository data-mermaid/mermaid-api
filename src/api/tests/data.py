import datetime
from datetime import datetime as dt

from django.conf import settings
from django.contrib.gis.geos import Point
from jose import jwt

from api.models.base import AuthUser, Profile
from api.models.mermaid import (
    BeltTransectWidth,
    BeltTransectWidthCondition,
    BenthicAttribute,
    Country,
    Current,
    FishFamily,
    FishGenus,
    FishSizeBin,
    FishSpecies,
    HabitatComplexityScore,
    Management,
    ManagementParty,
    Project,
    ProjectProfile,
    ReefExposure,
    ReefSlope,
    ReefType,
    ReefZone,
    RelativeDepth,
    SampleEvent,
    Site,
    Tide,
    Visibility,
)


class MockRequest:
    def __init__(self, user=None, token=None):
        self.user = user
        self.GET = {}
        self.query_params = {}
        if token:
            self.META = {"HTTP_AUTHORIZATION": "Bearer {}".format(token)}
        else:
            self.META = {}


class TestDataMixin(object):
    def timestamp(self):
        return (dt.utcnow() - dt(1970, 1, 1)).total_seconds()

    def create_token(self, sub):
        token_header = {"typ": "JWT", "alg": "HS256"}
        issued_at = self.timestamp()
        expiration_time = self.timestamp() + 60
        token_payload = {
            "iss": "https://datamermaid.auth0.com/",
            "sub": sub,
            "aud": "https://api.datamermaid.com",
            "iat": issued_at,
            "exp": expiration_time,
        }
        return jwt.encode(
            token_payload,
            key=settings.MERMAID_API_SIGNING_SECRET,
            algorithm="HS256",
            headers=token_header,
        )

    def load_fishattributes(self):
        self.fish_family1, _ = FishFamily.objects.get_or_create(name="Fish Family 1")
        self.fish_family2, _ = FishFamily.objects.get_or_create(name="Fish Family 2")
        self.fish_family3, _ = FishFamily.objects.get_or_create(name="Fish Family 3")

        self.fish_genus1, _ = FishGenus.objects.get_or_create(
            family=self.fish_family1, name="Fish Genus 1"
        )
        self.fish_genus2, _ = FishGenus.objects.get_or_create(
            family=self.fish_family2, name="Fish Genus 2"
        )
        self.fish_genus3, _ = FishGenus.objects.get_or_create(
            family=self.fish_family3, name="Fish Genus 3"
        )

        self.fish_species1, is_new = FishSpecies.objects.get_or_create(
            genus_id=self.fish_genus1.id, name="Fish Species 1"
        )
        if is_new:
            self.fish_species1.biomass_constant_a = 0.010000
            self.fish_species1.biomass_constant_b = 3.010000
            self.fish_species1.biomass_constant_c = 1
            self.fish_species1.save()

        self.fish_species2, is_new = FishSpecies.objects.get_or_create(
            genus=self.fish_genus2, name="Fish Species 2"
        )
        if is_new:
            self.fish_species2.biomass_constant_a = 0.020000
            self.fish_species2.biomass_constant_b = 3.020000
            self.fish_species2.biomass_constant_c = 1
            self.fish_species2.save()

        self.fish_species3, is_new = FishSpecies.objects.get_or_create(
            genus=self.fish_genus3, name="Fish Species 3"
        )
        if is_new:
            self.fish_species3.biomass_constant_a = 0.030000
            self.fish_species3.biomass_constant_b = 3.030000
            self.fish_species3.biomass_constant_c = 1
            self.fish_species3.save()

    def unload_fishattributes(self):
        self.fish_species1.delete()
        self.fish_species2.delete()
        self.fish_species3.delete()
        self.fish_genus1.delete()
        self.fish_genus2.delete()
        self.fish_genus3.delete()
        self.fish_family1.delete()
        self.fish_family2.delete()
        self.fish_family3.delete()

        self.fish_species1 = None
        self.fish_species2 = None
        self.fish_species3 = None
        self.fish_genus1 = None
        self.fish_genus2 = None
        self.fish_genus3 = None
        self.fish_family1 = None
        self.fish_family2 = None
        self.fish_family3 = None

    def load_benthicattributes(self):
        self.benthic_attribute1a, _ = BenthicAttribute.objects.get_or_create(name="Macroalgae")

        self.benthic_attribute1b, _ = BenthicAttribute.objects.get_or_create(
            name="Red Fleshy Algae", parent=self.benthic_attribute1a
        )

        self.benthic_attribute2a, _ = BenthicAttribute.objects.get_or_create(name="Hard coral")

        self.benthic_attribute2b, _ = BenthicAttribute.objects.get_or_create(
            name="Acroporidae", parent=self.benthic_attribute2a
        )

        self.benthic_attribute2c, _ = BenthicAttribute.objects.get_or_create(
            name="Astreopora", parent=self.benthic_attribute2b
        )

        self.benthic_attribute2d, _ = BenthicAttribute.objects.get_or_create(
            name="Faviidae", parent=self.benthic_attribute2a
        )
        self.benthic_attribute2e, _ = BenthicAttribute.objects.get_or_create(
            name="Erythrastrea", parent=self.benthic_attribute2d
        )

    def unload_benthicattributes(self):
        self.benthic_attribute1a.delete()
        self.benthic_attribute1b.delete()
        self.benthic_attribute2a.delete()
        self.benthic_attribute2b.delete()
        self.benthic_attribute2c.delete()
        self.benthic_attribute2d.delete()
        self.benthic_attribute2e.delete()

        self.benthic_attribute1a = None
        self.benthic_attribute1b = None
        self.benthic_attribute2a = None
        self.benthic_attribute2b = None
        self.benthic_attribute2c = None
        self.benthic_attribute2d = None
        self.benthic_attribute2e = None

    def load_choices(self):
        self.country1, _ = Country.objects.get_or_create(iso="AL", name="Atlantis")
        self.country2, _ = Country.objects.get_or_create(iso="CA", name="Canada")
        self.country3, _ = Country.objects.get_or_create(iso="US", name="United States")

        self.reef_type1, _ = ReefType.objects.get_or_create(name="reeftype1")
        self.reef_type2, _ = ReefType.objects.get_or_create(name="reeftype2")
        self.reef_type3, _ = ReefType.objects.get_or_create(name="reeftype3")

        self.reef_zone1, _ = ReefZone.objects.get_or_create(name="reefzone1")
        self.reef_zone2, _ = ReefZone.objects.get_or_create(name="reefzone2")
        self.reef_zone3, _ = ReefZone.objects.get_or_create(name="reefzone3")

        self.reef_exposure1, _ = ReefExposure.objects.get_or_create(name="reefexp1", val=1)
        self.reef_exposure2, _ = ReefExposure.objects.get_or_create(name="reefexp2", val=2)
        self.reef_exposure3, _ = ReefExposure.objects.get_or_create(name="reefexp3", val=3)

        self.visibility1, _ = Visibility.objects.get_or_create(name="Near", val=1)
        self.visibility2, _ = Visibility.objects.get_or_create(name="Mid", val=2)
        self.visibility3, _ = Visibility.objects.get_or_create(name="Far", val=3)

        self.current1, _ = Current.objects.get_or_create(name="Weak", val=1)
        self.current2, _ = Current.objects.get_or_create(name="Moderate", val=2)
        self.current2, _ = Current.objects.get_or_create(name="Strong", val=3)

        self.relative_depth1, _ = RelativeDepth.objects.get_or_create(name="Shallow")
        self.relative_depth2, _ = RelativeDepth.objects.get_or_create(name="Deep")

        self.tide1, _ = Tide.objects.get_or_create(name="Low")
        self.tide2, _ = Tide.objects.get_or_create(name="High")

        self.belt_transect_width1, _ = BeltTransectWidth.objects.get_or_create(name="2m")
        self.belt_transect_width2, _ = BeltTransectWidth.objects.get_or_create(name="5m")

        (
            self.belt_transect_width1_condition,
            _,
        ) = BeltTransectWidthCondition.objects.get_or_create(
            belttransectwidth=self.belt_transect_width1, val=2
        )
        (
            self.belt_transect_width2_condition,
            _,
        ) = BeltTransectWidthCondition.objects.get_or_create(
            belttransectwidth=self.belt_transect_width2, val=5
        )

        self.reef_slope1, _ = ReefSlope.objects.get_or_create(name="flat", val=1)
        self.reef_slope2, _ = ReefSlope.objects.get_or_create(name="slope", val=2)
        self.reef_slope3, _ = ReefSlope.objects.get_or_create(name="wall", val=3)

        (
            self.habitat_complexity_score1,
            _,
        ) = HabitatComplexityScore.objects.get_or_create(name="no vertical relief", val=1)
        (
            self.habitat_complexity_score2,
            _,
        ) = HabitatComplexityScore.objects.get_or_create(name="low", val=2)
        (
            self.habitat_complexity_score3,
            _,
        ) = HabitatComplexityScore.objects.get_or_create(name="exceptionally complex", val=3)

        self.management_party1, _ = ManagementParty.objects.get_or_create(name="Government")
        self.management_party2, _ = ManagementParty.objects.get_or_create(name="NGO")
        self.management_party3, _ = ManagementParty.objects.get_or_create(name="Private Sector")

        self.fish_size_bin1, _ = FishSizeBin.objects.get_or_create(val="1")
        self.fish_size_bin2, _ = FishSizeBin.objects.get_or_create(val="5")
        self.fish_size_bin3, _ = FishSizeBin.objects.get_or_create(val="10")

    def unload_choices(self):
        self.country1.delete()
        self.country2.delete()
        self.country3.delete()
        self.reef_type1.delete()
        self.reef_type2.delete()
        self.reef_type3.delete()
        self.reef_zone1.delete()
        self.reef_zone2.delete()
        self.reef_zone3.delete()
        self.reef_exposure1.delete()
        self.reef_exposure2.delete()
        self.reef_exposure3.delete()
        self.visibility1.delete()
        self.visibility2.delete()
        self.visibility3.delete()
        self.current1.delete()
        self.current2.delete()
        self.current2.delete()
        self.relative_depth1.delete()
        self.relative_depth2.delete()
        self.tide1.delete()
        self.tide2.delete()
        self.belt_transect_width1.delete()
        self.belt_transect_width2.delete()
        self.reef_slope1.delete()
        self.reef_slope2.delete()
        self.reef_slope3.delete()
        self.habitat_complexity_score1.delete()
        self.habitat_complexity_score2.delete()
        self.habitat_complexity_score3.delete()
        self.management_party1.delete()
        self.management_party2.delete()
        self.management_party3.delete()
        self.fish_size_bin1.delete()
        self.fish_size_bin2.delete()
        self.fish_size_bin3.delete()

        self.country1 = None
        self.country2 = None
        self.country3 = None
        self.reef_type1 = None
        self.reef_type2 = None
        self.reef_type3 = None
        self.reef_zone1 = None
        self.reef_zone2 = None
        self.reef_zone3 = None
        self.reef_exposure1 = None
        self.reef_exposure2 = None
        self.reef_exposure3 = None
        self.visibility1 = None
        self.visibility2 = None
        self.visibility3 = None
        self.current1 = None
        self.current2 = None
        self.current2 = None
        self.relative_depth1 = None
        self.relative_depth2 = None
        self.tide1 = None
        self.tide2 = None
        self.belt_transect_width1 = None
        self.belt_transect_width2 = None
        self.reef_slope1 = None
        self.reef_slope2 = None
        self.reef_slope3 = None
        self.habitat_complexity_score1 = None
        self.habitat_complexity_score2 = None
        self.habitat_complexity_score3 = None
        self.management_party1 = None
        self.management_party2 = None
        self.management_party3 = None
        self.fish_size_bin1 = None
        self.fish_size_bin2 = None
        self.fish_size_bin3 = None

    def load_projects(self):
        self.project1, _ = Project.objects.get_or_create(name="Test Project 1", status=Project.OPEN)
        self.project2, _ = Project.objects.get_or_create(
            name="Test Project 2", status=Project.LOCKED
        )

    def unload_projects(self):
        self.project1.delete()
        self.project2.delete()

        self.project1 = None
        self.project2 = None

    def load_profiles(self):
        self.profile1, _ = Profile.objects.get_or_create(
            email="profile1@mermaidcollect.org", first_name="Philip", last_name="Glass"
        )

        self.authuser1, _ = AuthUser.objects.get_or_create(
            profile=self.profile1, user_id="test|profile1"
        )

        self.profile1_token = self.create_token(self.authuser1.user_id)

        self.profile2, _ = Profile.objects.get_or_create(
            email="collector@mermaidcollect.org",
            first_name="Johann",
            last_name="Pachelbel",
        )

        self.authuser2, _ = AuthUser.objects.get_or_create(
            profile=self.profile2, user_id="test|profile2"
        )

        self.profile2_token = self.create_token(self.authuser2.user_id)

    def unload_profiles(self):
        self.authuser1.delete()
        self.authuser2.delete()
        self.profile1.delete()
        self.profile2.delete()

        self.profile1 = None
        self.authuser1 = None
        self.profile1_token = None
        self.profile2 = None
        self.authuser2 = None
        self.profile2_token = None

    def load_project_profiles(self):
        self.load_projects()
        self.load_profiles()

        self.project1_admin, _ = ProjectProfile.objects.get_or_create(
            project=self.project1, profile=self.profile1, role=ProjectProfile.ADMIN
        )

        self.project1_collector, _ = ProjectProfile.objects.get_or_create(
            project=self.project1, profile=self.profile2, role=ProjectProfile.COLLECTOR
        )

        self.project2_admin, _ = ProjectProfile.objects.get_or_create(
            project=self.project2, profile=self.profile2, role=ProjectProfile.ADMIN
        )

        self.project2_collector, _ = ProjectProfile.objects.get_or_create(
            project=self.project2, profile=self.profile1, role=ProjectProfile.COLLECTOR
        )

    def unload_project_profiles(self):
        self.project1_admin.delete()
        self.project1_collector.delete()
        self.project2_admin.delete()
        self.project2_collector.delete()

        self.project1_admin = None
        self.project1_collector = None
        self.project2_admin = None
        self.project2_collector = None

    def load_managements(self):
        self.load_projects()
        self.load_choices()
        self.management1, is_created1 = Management.objects.get_or_create(
            project=self.project1,
            est_year=2000,
            name="Management1",
            notes="Hey what's up!!",
        )
        if is_created1 is True:
            self.management1.parties.add(self.management_party1)

        self.management2, is_created2 = Management.objects.get_or_create(
            project=self.project2,
            est_year=2000,
            name="Management2",
            notes="Hey what's up!!",
        )
        if is_created2 is True:
            self.management2.parties.add(self.management_party1)
            self.management2.parties.add(self.management_party2)

    def unload_managements(self):
        self.management1.delete()
        self.management2.delete()

        self.management1 = None
        self.management2 = None

    def load_sites(self):
        self.load_projects()
        self.load_choices()
        self.site1, _ = Site.objects.get_or_create(
            project=self.project1,
            name="Site 1",
            location=Point(1, 1, srid=4326),
            country=self.country1,
            reef_type=self.reef_type1,
            exposure=self.reef_exposure1,
            reef_zone=self.reef_zone1,
        )

        self.site2, _ = Site.objects.get_or_create(
            project=self.project2,
            name="Site 2",
            location=Point(1.2, 1.2, srid=4326),
            country=self.country2,
            reef_type=self.reef_type2,
            exposure=self.reef_exposure2,
            reef_zone=self.reef_zone2,
        )

    def unload_sites(self):
        self.site1.delete()
        self.site2.delete()

        self.site1 = None
        self.site2 = None

    def load_sample_events(self):
        self.load_choices()
        self.load_sites()
        self.load_managements()
        self.load_choices()

        try:
            self.sample_event1 = SampleEvent.objects.get(
                site=self.site1,
                management=self.management1,
                sample_date=datetime.date(2018, 7, 13),
            )
        except SampleEvent.DoesNotExist:
            self.sample_event1 = SampleEvent.objects.create(
                site=self.site1,
                management=self.management1,
                sample_date=datetime.date(2018, 7, 13),
            )

        try:
            self.sample_event2 = SampleEvent.objects.get(
                site=self.site2,
                management=self.management2,
                sample_date=datetime.date(2018, 7, 14),
            )
        except SampleEvent.DoesNotExist:
            self.sample_event2 = SampleEvent.objects.create(
                site=self.site2,
                management=self.management2,
                sample_date=datetime.date(2018, 7, 14),
            )

    def unload_sample_events(self):
        self.sample_event1.delete()
        self.sample_event2.delete()

        self.sample_event1 = None
        self.sample_event2 = None
