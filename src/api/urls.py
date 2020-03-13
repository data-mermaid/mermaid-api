from django.conf.urls import url
from rest_framework_nested import routers

from .resources.me import MeViewSet
from .resources.profile import ProfileViewSet
from .resources.project import ProjectViewSet
from .resources.site import SiteViewSet
from .resources.management import ManagementViewSet
from .resources.benthic_attribute import BenthicAttributeViewSet
from .resources.fish_family import FishFamilyViewSet
from .resources.fish_genus import FishGenusViewSet
from .resources.fish_species import FishSpeciesViewSet
from .resources.choices import ChoiceViewSet
from .resources.collect_record import CollectRecordViewSet
from .resources.observer import ObserverViewSet
from .resources.project_profile import ProjectProfileViewSet
from .resources.psite import PSiteViewSet
from .resources.pmanagement import PManagementViewSet
from .resources.sample_event import SampleEventViewSet
from .resources.benthic_lit import BenthicLITViewSet
from .resources.benthic_pit import BenthicPITViewSet
from .resources.habitat_complexity import HabitatComplexityViewSet
from .resources.belt_fish import BeltFishViewSet
from .resources.bleaching_quadrat_collection import BleachingQuadratCollectionViewSet
from .resources.benthic_transect import BenthicTransectViewSet
from .resources.quadrat_collection import QuadratCollectionViewSet
from .resources.fish_belt_transect import FishBeltTransectViewSet
from .resources.obs_belt_fish import ObsBeltFishViewSet
from .resources.obs_benthic_lit import ObsBenthicLITViewSet
from .resources.obs_benthic_pit import ObsBenthicPITViewSet
from .resources.obs_habitat_complexity import ObsHabitatComplexityViewSet
from .resources.obs_colonies_bleached import ObsColoniesBleachedViewSet
from .resources.obs_quadrat_benthic_percent import ObsQuadratBenthicPercentViewSet

from .resources.sample_units.beltfishmethod import (
    BeltFishMethodView,
    BeltFishProjectMethodObsView,
    BeltFishProjectMethodSUView,
    BeltFishProjectMethodSEView,
)
from .resources.sample_units.benthiclitmethod import BenthicLITMethodView
from .resources.sample_units.benthicpitmethod import BenthicPITMethodView
from .resources.sample_units.habitatcomplexitymethod import HabitatComplexityMethodView
from .resources.sample_units.bleachingquadratcollectionmethod import (
    BleachingQuadratCollectionMethodView,
)
from .resources.sample_units.sample_unit_methods import SampleUnitMethodView

from .resources.fish_size import FishSizeViewSet
from .resources.version import AppVersionViewSet
from .resources.health import health
from .resources.project_tag import ProjectTagViewSet


# APP-WIDE - BASE
router = routers.DefaultRouter()

router.register(r"me", MeViewSet, "me")
router.register(r"profiles", ProfileViewSet, "profile")
router.register(r"version", AppVersionViewSet, "app_version")


# APP-WIDE - MERMAID

# management
router.register(r"projects", ProjectViewSet, "project")
router.register(r"sites", SiteViewSet, "site")
router.register(r"managements", ManagementViewSet, "management")
router.register(r"projecttags", ProjectTagViewSet, "projecttag")

# observation attributes
router.register(r"benthicattributes", BenthicAttributeViewSet, "benthicattribute")
router.register(r"fishfamilies", FishFamilyViewSet, "fishfamily")
router.register(r"fishgenera", FishGenusViewSet, "fishgenus")
router.register(r"fishspecies", FishSpeciesViewSet, "fishspecies")
router.register(r"fishsizes", FishSizeViewSet, "fishsizes")

# choices
router.register(r"choices", ChoiceViewSet, "choice")

# PROJECT-SPECIFIC - MERMAID
project_router = routers.NestedSimpleRouter(router, r"projects", lookup="project")
# Note there's nothing stopping us from creating additional versions of these endpoints that do not
# depend on project pk if we want to enable some kind of access for superusers or (limited-field) public users

# collect
project_router.register(r"collectrecords", CollectRecordViewSet, "collectrecords")

project_router.register(r"observers", ObserverViewSet, "observer")
project_router.register(r"project_profiles", ProjectProfileViewSet, "project_profile")
project_router.register(r"sites", PSiteViewSet, "psite")
project_router.register(r"managements", PManagementViewSet, "pmanagement")
project_router.register(r"sampleevents", SampleEventViewSet, "sampleevent")

# sample units
project_router.register(r"benthictransects", BenthicTransectViewSet, "benthictransect")
project_router.register(
    r"fishbelttransects", FishBeltTransectViewSet, "fishbelttransect"
)
project_router.register(
    r"quadratcollections", QuadratCollectionViewSet, "quadratcollection"
)

# multi model sample unit method views
project_router.register(
    r"beltfishes/obstransectbeltfishes",
    BeltFishProjectMethodObsView,
    "obstransectbeltfish",
)
project_router.register(
    r"beltfishes/sampleunits", BeltFishProjectMethodSUView, "sampleunit"
)
project_router.register(
   r"beltfishes/sampleevents", BeltFishProjectMethodSEView, "sampleevent"
)

# multi model sample unit method reports
project_router.register(
    r"beltfishtransectmethods", BeltFishMethodView, "beltfishtransectmethod"
)
project_router.register(
    r"benthiclittransectmethods", BenthicLITMethodView, "benthiclittransectmethod"
)
project_router.register(
    r"benthicpittransectmethods", BenthicPITMethodView, "benthicpittransectmethod"
)
project_router.register(
    r"habitatcomplexitytransectmethods",
    HabitatComplexityMethodView,
    "habitatcomplexitytransectmethod",
)
project_router.register(
    r"bleachingquadratcollectionmethods",
    BleachingQuadratCollectionMethodView,
    "bleachingquadratcollectionmethod",
)
project_router.register(r"sampleunitmethods", SampleUnitMethodView, "sampleunitmethod")

# straight-up sample unit methods (not typically used on their own)
project_router.register(r"benthiclits", BenthicLITViewSet, "benthiclit")
project_router.register(r"benthicpits", BenthicPITViewSet, "benthicpit")
project_router.register(
    r"habitatcomplexities", HabitatComplexityViewSet, "habitatcomplexity"
)
project_router.register(r"beltfishes", BeltFishViewSet, "beltfish")
project_router.register(
    r"bleachingquadratcollections",
    BleachingQuadratCollectionViewSet,
    "bleachingquadratcollection",
)

# observations
project_router.register(r"obsbenthiclits", ObsBenthicLITViewSet, "obsbenthiclit")
project_router.register(r"obsbenthicpits", ObsBenthicPITViewSet, "obsbenthicpit")
project_router.register(
    r"obscoloniesbleached", ObsColoniesBleachedViewSet, "obscoloniesbleached"
)
project_router.register(
    r"obshabitatcomplexities", ObsHabitatComplexityViewSet, "obshabitatcomplexity"
)
project_router.register(
    r"obsquadratbenthicpercent",
    ObsQuadratBenthicPercentViewSet,
    "obsquadratbenthicpercent",
)
project_router.register(
    r"obstransectbeltfishs", ObsBeltFishViewSet, "obstransectbeltfish"
)


api_urls = router.urls + project_router.urls
api_urls += (url(r"^health/$", health),)
