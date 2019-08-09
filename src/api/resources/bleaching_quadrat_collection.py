import django_filters
from .base import BaseAPIFilterSet, BaseAPISerializer, BaseProjectApiViewSet

from ..models import BleachingQuadratCollection


class BleachingQuadratCollectionSerializer(BaseAPISerializer):
    class Meta:
        model = BleachingQuadratCollection
        exclude = []
        extra_kwargs = {}


class BleachingQuadratCollectionFilterSet(BaseAPIFilterSet):
    class Meta:
        model = BleachingQuadratCollection
        fields = ["quadrat", "quadrat__sample_event"]


class BleachingQuadratCollectionViewSet(BaseProjectApiViewSet):
    serializer_class = BleachingQuadratCollectionSerializer
    queryset = BleachingQuadratCollection.objects.all()
    filter_class = BleachingQuadratCollectionFilterSet
