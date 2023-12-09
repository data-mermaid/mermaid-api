from .attributes_ingester import BenthicIngester, FishIngester  # noqa: F401
from .benthiclit_serializer import BenthicLITCSVSerializer
from .benthicpit_serializer import BenthicPITCSVSerializer
from .benthicpqt_serializer import BenthicPhotoQTCSVSerializer
from .bleaching_serializer import BleachingCSVSerializer
from .fishbelt_serializer import FishBeltCSVSerializer
from .habitatcomplexity_serializer import HabitatComplexityCSVSerializer

ingest_serializers = [
    BenthicLITCSVSerializer,
    BenthicPhotoQTCSVSerializer,
    BenthicPITCSVSerializer,
    BleachingCSVSerializer,
    FishBeltCSVSerializer,
    HabitatComplexityCSVSerializer,
]
