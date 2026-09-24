from .attributes_ingester import BenthicIngester, FishIngester  # noqa: F401
from .benthiclit_serializer import BenthicLITCSVSerializer
from .benthicpit_serializer import BenthicPITCSVSerializer
from .benthicpqt_serializer import BenthicPhotoQTCSVSerializer
from .bleaching_serializer import BleachingCSVSerializer
from .fishbelt_serializer import FishBeltCSVSerializer
from .habitatcomplexity_serializer import HabitatComplexityCSVSerializer
from .macroinvertebrate_serializer import MacroInvertebrateCSVSerializer

ingest_serializers = [
    BenthicLITCSVSerializer,
    BenthicPhotoQTCSVSerializer,
    BenthicPITCSVSerializer,
    BleachingCSVSerializer,
    FishBeltCSVSerializer,
    HabitatComplexityCSVSerializer,
    MacroInvertebrateCSVSerializer,
]

# Protocols in PROTOCOL_MAP that do not yet have ingest/submission support.
# Tests and endpoints that require a full ingest implementation should skip these.
INGEST_PROTOCOLS_NOT_YET_IMPLEMENTED = frozenset()
