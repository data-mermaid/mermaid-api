from django.urls import re_path
from rest_framework_nested import routers

from .resources.benthic_attribute import BenthicAttributeViewSet
from .resources.benthic_transect import BenthicTransectViewSet
from .resources.choices import ChoiceViewSet
from .resources.collect_record import CollectRecordViewSet
from .resources.contact import contact_mermaid, contact_project_admins
from .resources.fish_belt_transect import FishBeltTransectViewSet
from .resources.fish_family import FishFamilyViewSet
from .resources.fish_genus import FishGenusViewSet
from .resources.fish_grouping import FishGroupingViewSet
from .resources.fish_size import FishSizeViewSet
from .resources.fish_species import FishSpeciesViewSet
from .resources.health import health
from .resources.ingest_schema import ingest_schema_csv
from .resources.management import ManagementViewSet
from .resources.me import MeViewSet
from .resources.notification import NotificationViewSet
from .resources.observer import ObserverViewSet
from .resources.pmanagement import PManagementViewSet
from .resources.profile import ProfileViewSet
from .resources.project import ProjectViewSet
from .resources.project_profile import ProjectProfileViewSet
from .resources.project_sample_event_summaries import ProjectSummarySampleEventViewSet
from .resources.project_tag import ProjectTagViewSet
from .resources.psite import PSiteViewSet
from .resources.quadrat_collection import QuadratCollectionViewSet
from .resources.sample_event import SampleEventViewSet
from .resources.sampleunitmethods.beltfishmethod import (
    BeltFishMethodView,
    BeltFishProjectMethodObsView,
    BeltFishProjectMethodSEView,
    BeltFishProjectMethodSUView,
)
from .resources.sampleunitmethods.benthiclitmethod import (
    BenthicLITMethodView,
    BenthicLITProjectMethodObsView,
    BenthicLITProjectMethodSEView,
    BenthicLITProjectMethodSUView,
)
from .resources.sampleunitmethods.benthicphotoquadrattransectmethod import (
    BenthicPhotoQuadratTransectMethodView,
    BenthicPQTProjectMethodObsView,
    BenthicPQTProjectMethodSEView,
    BenthicPQTProjectMethodSUView,
)
from .resources.sampleunitmethods.benthicpitmethod import (
    BenthicPITMethodView,
    BenthicPITProjectMethodObsView,
    BenthicPITProjectMethodSEView,
    BenthicPITProjectMethodSUView,
)
from .resources.sampleunitmethods.bleachingquadratcollectionmethod import (
    BleachingQCProjectMethodObsColoniesBleachedView,
    BleachingQCProjectMethodObsQuadratBenthicPercentView,
    BleachingQCProjectMethodSEView,
    BleachingQCProjectMethodSUView,
    BleachingQuadratCollectionMethodView,
)
from .resources.sampleunitmethods.habitatcomplexitymethod import (
    HabitatComplexityMethodView,
    HabitatComplexityProjectMethodObsView,
    HabitatComplexityProjectMethodSEView,
    HabitatComplexityProjectMethodSUView,
)
from .resources.sampleunitmethods.sample_unit_methods import SampleUnitMethodView
from .resources.site import SiteViewSet
from .resources.summary_sample_event import SummarySampleEventView
from .resources.sync import vw_pull, vw_push

# APP-WIDE - BASE
router = routers.DefaultRouter()

router.register(r"me", MeViewSet, "me")
router.register(r"profiles", ProfileViewSet, "profile")


# APP-WIDE - MERMAID

# management/summary
router.register(r"projects", ProjectViewSet, "project")
router.register(r"sites", SiteViewSet, "site")
router.register(r"managements", ManagementViewSet, "management")
router.register(r"projecttags", ProjectTagViewSet, "projecttag")
router.register(r"summarysampleevents", SummarySampleEventView, "summarysampleevent")
router.register(r"notifications", NotificationViewSet, "notification")

# observation attributes
router.register(r"benthicattributes", BenthicAttributeViewSet, "benthicattribute")
router.register(r"fishfamilies", FishFamilyViewSet, "fishfamily")
router.register(r"fishgenera", FishGenusViewSet, "fishgenus")
router.register(r"fishspecies", FishSpeciesViewSet, "fishspecies")
router.register(r"fishgroupings", FishGroupingViewSet, "fishgrouping")

# choices
router.register(r"choices", ChoiceViewSet, "choice")
router.register(r"fishsizes", FishSizeViewSet, "fishsizes")

# project sample event summaries
router.register(
    r"project_summary_sample_event",
    ProjectSummarySampleEventViewSet,
    "project_summary_sample_event",
)

# PROJECT-SPECIFIC - MERMAID
project_router = routers.NestedSimpleRouter(router, r"projects", lookup="project")

# collect
project_router.register(r"collectrecords", CollectRecordViewSet, "collectrecords")

project_router.register(r"observers", ObserverViewSet, "observer")
project_router.register(r"project_profiles", ProjectProfileViewSet, "project_profile")
project_router.register(r"sites", PSiteViewSet, "psite")
project_router.register(r"managements", PManagementViewSet, "pmanagement")
project_router.register(r"sampleevents", SampleEventViewSet, "sampleevent")

# sample units
project_router.register(r"benthictransects", BenthicTransectViewSet, "benthictransect")
project_router.register(r"fishbelttransects", FishBeltTransectViewSet, "fishbelttransect")
project_router.register(r"quadratcollections", QuadratCollectionViewSet, "quadratcollection")

# multi model sample unit method views
project_router.register(
    r"beltfishes/obstransectbeltfishes",
    BeltFishProjectMethodObsView,
    "beltfishmethod-obs",
)
project_router.register(
    r"beltfishes/sampleunits", BeltFishProjectMethodSUView, "beltfishmethod-sampleunit"
)
project_router.register(
    r"beltfishes/sampleevents",
    BeltFishProjectMethodSEView,
    "beltfishmethod-sampleevent",
)

project_router.register(
    r"benthiclits/obstransectbenthiclits",
    BenthicLITProjectMethodObsView,
    "benthiclitmethod-obs",
)
project_router.register(
    r"benthiclits/sampleunits",
    BenthicLITProjectMethodSUView,
    "benthiclitmethod-sampleunit",
)
project_router.register(
    r"benthiclits/sampleevents",
    BenthicLITProjectMethodSEView,
    "benthiclitmethod-sampleevent",
)

project_router.register(
    r"benthicpits/obstransectbenthicpits",
    BenthicPITProjectMethodObsView,
    "benthicpitmethod-obs",
)
project_router.register(
    r"benthicpits/sampleunits",
    BenthicPITProjectMethodSUView,
    "benthicpitmethod-sampleunit",
)
project_router.register(
    r"benthicpits/sampleevents",
    BenthicPITProjectMethodSEView,
    "benthicpitmethod-sampleevent",
)

project_router.register(
    r"bleachingqcs/obscoloniesbleacheds",
    BleachingQCProjectMethodObsColoniesBleachedView,
    "coloniesbleachedmethod-obs",
)
project_router.register(
    r"bleachingqcs/obsquadratbenthicpercents",
    BleachingQCProjectMethodObsQuadratBenthicPercentView,
    "quadratbenthicpercentmethod-obs",
)
project_router.register(
    r"bleachingqcs/sampleunits",
    BleachingQCProjectMethodSUView,
    "bleachingqcsmethod-sampleunit",
)
project_router.register(
    r"bleachingqcs/sampleevents",
    BleachingQCProjectMethodSEView,
    "bleachingqcsmethod-sampleevent",
)

project_router.register(
    r"habitatcomplexities/obshabitatcomplexities",
    HabitatComplexityProjectMethodObsView,
    "habitatcomplexitymethod-obs",
)
project_router.register(
    r"habitatcomplexities/sampleunits",
    HabitatComplexityProjectMethodSUView,
    "habitatcomplexitymethod-sampleunit",
)
project_router.register(
    r"habitatcomplexities/sampleevents",
    HabitatComplexityProjectMethodSEView,
    "habitatcomplexitymethod-sampleevent",
)

project_router.register(
    r"benthicpqts/obstransectbenthicpqts",
    BenthicPQTProjectMethodObsView,
    "benthicpqtmethod-obs",
)
project_router.register(
    r"benthicpqts/sampleunits",
    BenthicPQTProjectMethodSUView,
    "benthicpqtmethod-sampleunit",
)
project_router.register(
    r"benthicpqts/sampleevents",
    BenthicPQTProjectMethodSEView,
    "benthicpqtmethod-sampleevent",
)


# multi model sample unit method reports
project_router.register(r"beltfishtransectmethods", BeltFishMethodView, "beltfishtransectmethod")
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
project_router.register(
    r"benthicphotoquadrattransectmethods",
    BenthicPhotoQuadratTransectMethodView,
    "benthicphotoquadrattransectmethod",
)
project_router.register(r"sampleunitmethods", SampleUnitMethodView, "sampleunitmethod")


api_urls = (
    router.urls
    + project_router.urls
    + [
        re_path(r"^contactmermaid/$", contact_mermaid, name="contactmermaid"),
        re_path(r"^contactprojectadmins/$", contact_project_admins, name="contactprojectadmins"),
        re_path(
            r"^ingest_schema_csv/(?P<sample_unit>\w+)/$",
            ingest_schema_csv,
            name="ingest-schemas-csv",
        ),
        re_path(r"^health/$", health),
        re_path(r"^pull/$", vw_pull),
        re_path(r"^push/$", vw_push),
    ]
)
