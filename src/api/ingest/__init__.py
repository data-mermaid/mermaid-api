from .attributes_ingester import BenthicIngester, FishIngester
from .benthiclit_serializer import *
from .benthicpit_serializer import *
from .benthicpqt_serializer import *
from .bleaching_serializer import *
from .fishbelt_serializer import *
from .habitatcomplexity_serializer import *
from .serializers import *

ingest_serializers = [
    BenthicLITCSVSerializer,
    BenthicPhotoQTCSVSerializer,
    BenthicPITCSVSerializer,
    BleachingCSVSerializer,
    FishBeltCSVSerializer,
    HabitatComplexityCSVSerializer,
]
