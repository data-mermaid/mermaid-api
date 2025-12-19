from rest_framework.exceptions import ParseError

from ...exceptions import check_uuid
from ...models import (
    BeltFish,
    BenthicLIT,
    BenthicPhotoQuadratTransect,
    BenthicPIT,
    BleachingQuadratCollection,
    HabitatComplexity,
)

# Shared protocol mappings used across validators
PROTOCOL_MODEL_MAP = {
    "benthiclit": BenthicLIT,
    "benthicpit": BenthicPIT,
    "fishbelt": BeltFish,
    "habitatcomplexity": HabitatComplexity,
    "bleachingqc": BleachingQuadratCollection,
    "benthicpqt": BenthicPhotoQuadratTransect,
}

PROTOCOL_SAMPLE_EVENT_PATH = {
    "benthiclit": "transect__sample_event",
    "benthicpit": "transect__sample_event",
    "fishbelt": "transect__sample_event",
    "habitatcomplexity": "transect__sample_event",
    "bleachingqc": "quadrat__sample_event",
    "benthicpqt": "quadrat_transect__sample_event",
}


def valid_id(uuid):
    try:
        uuid = check_uuid(uuid)
    except ParseError:
        return None
    return uuid
