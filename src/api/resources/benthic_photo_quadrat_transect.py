from ..models import BenthicPhotoQuadratTransect
from .base import BaseAPIFilterSet, BaseAPISerializer, BaseProjectApiViewSet


class BenthicPhotoQuadratTransectSerializer(BaseAPISerializer):
    class Meta:
        model = BenthicPhotoQuadratTransect
        exclude = []


class BenthicPhotoQuadratTransectFilterSet(BaseAPIFilterSet):
    class Meta:
        model = BenthicPhotoQuadratTransect
        fields = [
            "quadrat_transect",
            "quadrat_transect__sample_event",
        ]


class BenthicPhotoQuadratTransectViewSet(BaseProjectApiViewSet):
    serializer_class = BenthicPhotoQuadratTransectSerializer
    queryset = BenthicPhotoQuadratTransect.objects.all()
    filter_class = BenthicPhotoQuadratTransectFilterSet
