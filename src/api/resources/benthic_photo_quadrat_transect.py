from ..models import BenthicPhotoQuadratTransect
from .base import BaseAPISerializer


class BenthicPhotoQuadratTransectSerializer(BaseAPISerializer):
    class Meta:
        model = BenthicPhotoQuadratTransect
        exclude = []
