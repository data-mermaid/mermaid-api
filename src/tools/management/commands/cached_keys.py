from django.core.management.base import BaseCommand

from api.models import (
    BENTHICLIT_PROTOCOL,
    BENTHICPIT_PROTOCOL,
    BENTHICPQT_PROTOCOL,
    BLEACHINGQC_PROTOCOL,
    FISHBELT_PROTOCOL,
    HABITATCOMPLEXITY_PROTOCOL,
)
from api.resources.sampleunitmethods.beltfishmethod import (
    BeltFishProjectMethodObsView,
    BeltFishProjectMethodSEView,
    BeltFishProjectMethodSUView,
)
from api.resources.sampleunitmethods.benthiclitmethod import (
    BenthicLITProjectMethodObsView,
    BenthicLITProjectMethodSEView,
    BenthicLITProjectMethodSUView,
)
from api.resources.sampleunitmethods.benthicphotoquadrattransectmethod import (
    BenthicPQTProjectMethodObsView,
    BenthicPQTProjectMethodSEView,
    BenthicPQTProjectMethodSUView,
)
from api.resources.sampleunitmethods.benthicpitmethod import (
    BenthicPITProjectMethodObsView,
    BenthicPITProjectMethodSEView,
    BenthicPITProjectMethodSUView,
)
from api.resources.sampleunitmethods.bleachingquadratcollectionmethod import (
    BleachingQCProjectMethodObsColoniesBleachedView,
    BleachingQCProjectMethodObsQuadratBenthicPercentView,
    BleachingQCProjectMethodSEView,
    BleachingQCProjectMethodSUView,
)
from api.resources.sampleunitmethods.habitatcomplexitymethod import (
    HabitatComplexityProjectMethodObsView,
    HabitatComplexityProjectMethodSEView,
    HabitatComplexityProjectMethodSUView,
)
from api.utils import cached

PROTOCOL_CHOICES = [
    BENTHICLIT_PROTOCOL,
    BENTHICPIT_PROTOCOL,
    FISHBELT_PROTOCOL,
    HABITATCOMPLEXITY_PROTOCOL,
    BLEACHINGQC_PROTOCOL,
    BENTHICPQT_PROTOCOL,
]
LOOKUP = {
    FISHBELT_PROTOCOL: {
        "obs": BeltFishProjectMethodObsView,
        "su": BeltFishProjectMethodSUView,
        "se": BeltFishProjectMethodSEView,
    },
    "beltfish": {
        "obs": BeltFishProjectMethodObsView,
        "su": BeltFishProjectMethodSUView,
        "se": BeltFishProjectMethodSEView,
    },
    BENTHICLIT_PROTOCOL: {
        "obs": BenthicLITProjectMethodObsView,
        "su": BenthicLITProjectMethodSUView,
        "se": BenthicLITProjectMethodSEView,
    },
    BENTHICPQT_PROTOCOL: {
        "obs": BenthicPQTProjectMethodObsView,
        "su": BenthicPQTProjectMethodSUView,
        "se": BenthicPQTProjectMethodSEView,
    },
    BENTHICPIT_PROTOCOL: {
        "obs": BenthicPITProjectMethodObsView,
        "su": BenthicPITProjectMethodSUView,
        "se": BenthicPITProjectMethodSEView,
    },
    BLEACHINGQC_PROTOCOL: {
        "obs_percent": BleachingQCProjectMethodObsQuadratBenthicPercentView,
        "obs_colonies_bleached": BleachingQCProjectMethodObsColoniesBleachedView,
        "su": BleachingQCProjectMethodSUView,
        "se": BleachingQCProjectMethodSEView,
    },
    HABITATCOMPLEXITY_PROTOCOL: {
        "obs": HabitatComplexityProjectMethodObsView,
        "su": HabitatComplexityProjectMethodSUView,
        "se": HabitatComplexityProjectMethodSEView,
    },
}


class Command(BaseCommand):
    help = """Prints out expected sample unit method cached file keys.
    """

    def __init__(self):
        super(Command, self).__init__()

    def add_arguments(self, parser):
        parser.add_argument("project_id", type=str, help="Project ID")

        parser.add_argument(
            "protocol_name",
            type=str,
            choices=sorted(PROTOCOL_CHOICES + ["beltfish"]),
            help="Protocol name",
        )

    def _create_keys(self, project_id, viewset):
        add_fields = cached.make_viewset_cache_key(
            viewset,
            project_id,
            include_additional_fields=True,
            show_display_fields=False,
        )
        display_fields = cached.make_viewset_cache_key(
            viewset,
            project_id,
            include_additional_fields=False,
            show_display_fields=True,
        )

        return add_fields, display_fields

    def handle(self, *args, **options):
        project_id = options.get("project_id")
        protocol_name = options.get("protocol_name")

        viewsets = LOOKUP.get(protocol_name)

        print(f"Protocol: {protocol_name}\n")
        for key, viewset in viewsets.items():
            add_fields, display_fields = self._create_keys(project_id, viewset)
            print(f"{key} - system fields:\t{add_fields}")
            print(f"{key} - display fields:\t{display_fields}")
