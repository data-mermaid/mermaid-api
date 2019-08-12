from .base import BaseAPISerializer
from ..models import GrowthForm


class GrowthFormSerializer(BaseAPISerializer):

    class Meta:
        model = GrowthForm
        exclude = []
