from ..models import GrowthForm
from .base import BaseAPISerializer


class GrowthFormSerializer(BaseAPISerializer):
    class Meta:
        model = GrowthForm
        exclude = []
