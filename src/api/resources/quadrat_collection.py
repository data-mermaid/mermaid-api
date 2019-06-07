import django_filters
from base import BaseAPIFilterSet, BaseAPISerializer, BaseProjectApiViewSet

from ..models import QuadratCollection


class QuadratCollectionSerializer(BaseAPISerializer):
    class Meta:
        model = QuadratCollection
        exclude = []
        extra_kwargs = {
            "quadrat_size": {"error_messages": {"null": "Quadrat size is required"}}
        }


class QuadratCollectionFilterSet(BaseAPIFilterSet):
    class Meta:
        model = QuadratCollection
        exclude = []


class QuadratCollectionViewSet(BaseProjectApiViewSet):
    serializer_class = QuadratCollectionSerializer
    queryset = QuadratCollection.objects.all()
    filter_class = QuadratCollectionFilterSet
