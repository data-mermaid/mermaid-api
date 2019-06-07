import datetime
from datetime import datetime as dt
from jose import jwt
from django.conf import settings
from django.test import TestCase
from django.contrib.gis.geos import Point

from api.models import BenthicPIT
from api.models import BenthicTransect
from api.models import Site
from api.models import ReefType
from api.models import ReefExposure
from api.models import ReefZone
from api.models import Country
from api.models import Project
from api.models import Profile
from api.models import AuthUser
from api.models import ProjectProfile
from api.models import ManagementParty
from api.models import FishFamily
from api.models import FishGenus
from api.models import FishSpecies
from api.models import FishSizeBin
from api.models import Visibility
from api.models import Current
from api.models import RelativeDepth
from api.models import SampleEvent
from api.models import Tide
from api.models import BeltTransectWidth
from api.models import Management


class BaseTestCase(TestCase):

    def setUp(self):
        self.admin_profile = Profile.objects.create(
            email='admin@mermaidcollect.org',
            first_name='Philip',
            last_name='Glass'
        )

        self.admin_authuser = AuthUser.objects.create(
            profile=self.admin_profile,
            user_id='test|admin1234'
        )

        self.admin_token = self.create_token(self.admin_authuser.user_id)

        self.collector_profile = Profile.objects.create(
            email='collector@mermaidcollect.org',
            first_name='Johann',
            last_name='Pachelbel'
        )

        self.collector_authuser = AuthUser.objects.create(
            profile=self.collector_profile,
            user_id='test|collector1234'
        )

        self.collector_token = self.create_token(self.collector_authuser.user_id)

        self.project = Project.objects.create(name='Test Project',
                                              status=Project.OPEN)
        self.admin_project_profile = ProjectProfile.objects.create(
            project=self.project,
            profile=self.admin_profile,
            role=ProjectProfile.ADMIN
        )

        self.collector_project_profile = ProjectProfile.objects.create(
            project=self.project,
            profile=self.collector_profile,
            role=ProjectProfile.COLLECTOR
        )

        self.country = Country.objects.create(iso='AL', name='Atlantis')
        self.reef_type = ReefType.objects.create(name='reeftype1')
        self.reef_zone = ReefZone.objects.create(name='reefzone1')
        self.reef_exposure = ReefExposure.objects.create(name='reefexp1',
                                                         val=1)
        self.visibility = Visibility.objects.create(name='Far', val=1)
        self.current = Current.objects.create(name='Strong', val=5)
        self.relative_depth = RelativeDepth.objects.create(name='Very Deep')
        self.tide = Tide.objects.create(name='Is High')
        self.belt_transect_width = BeltTransectWidth.objects.create(val=2)

        self.site1 = Site.objects.create(project=self.project,
                                         name='Site ABC',
                                         location=Point(1, 1, srid=4326),
                                         country=self.country,
                                         reef_type=self.reef_type,
                                         exposure=self.reef_exposure,
                                         reef_zone=self.reef_zone)

        self.site2 = Site.objects.create(project=self.project,
                                         name='Site DEF',
                                         location=Point(1.2, 1.2, srid=4326),
                                         country=self.country,
                                         reef_type=self.reef_type,
                                         exposure=self.reef_exposure,
                                         reef_zone=self.reef_zone)

        self.management_party = ManagementParty.objects.create(name='Open')
        self.management = Management.objects.create(
            project=self.project,
            est_year=2000,
            name='Test Management',
            notes='Hey what\'s up!!'
        )
        self.management.parties.add(self.management_party)

        self.fish_size_bin = FishSizeBin.objects.create(val=7.5)
        self.fish_family = FishFamily.objects.create(name='Clown Fish Family')
        self.fish_genus = FishGenus.objects.create(family=self.fish_family, name='Clown Fish Genus')
        self.fish_species = FishSpecies.objects.create(
            genus=self.fish_genus,
            name='Clown Fish',
            biomass_constant_a=0.01,
            biomass_constant_b=3.06,
            biomass_constant_c=1,
        )

        self.sample_event = SampleEvent.objects.create(
            site=self.site1,
            management=self.management,
            sample_date=datetime.date(2018, 7, 13),
            sample_time=datetime.time(12, 0, 0),
            depth=1.1,
            relative_depth=self.relative_depth
        )

        self.benthic_transect = BenthicTransect.objects.create(
            number=1,
            len_surveyed=100,
            sample_event=self.sample_event
        )

        self.benthic_pit = BenthicPIT.objects.create(
            transect=self.benthic_transect,
            interval_size=1
        )

    def tearDown(self):
        self.admin_project_profile.delete()
        self.collector_project_profile.delete()
        self.admin_profile.delete()
        self.collector_profile.delete()
        self.sample_event.delete()
        self.benthic_transect.delete()
        self.site1.delete()
        self.site2.delete()
        self.project.delete()
        self.country.delete()
        self.fish_size_bin.delete()
        self.visibility.delete()
        self.current.delete()
        self.relative_depth.delete()
        self.tide.delete()
        self.belt_transect_width.delete()
        self.reef_type.delete()
        self.reef_zone.delete()
        self.management_party.delete()
        self.fish_family.delete()

    def timestamp(self):
        return (dt.utcnow() - dt(1970, 1, 1)).total_seconds()

    def create_token(self, sub):
        token_header = {
            "typ": "JWT",
            "alg": "HS256"
        }
        issued_at = self.timestamp()
        expiration_time = self.timestamp() + 60
        token_payload = {
            "iss": "https://datamermaid.auth0.com/",
            "sub": sub,
            "aud": "https://api.datamermaid.com",
            "iat": issued_at,
            "exp": expiration_time
        }

        return jwt.encode(
            token_payload,
            key=settings.MERMAID_API_SIGNING_SECRET,
            algorithm='HS256',
            headers=token_header
        )
