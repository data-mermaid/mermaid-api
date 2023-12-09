from ..models import QuadratCollection
from .base import BaseProjectApiViewSet
from .sample_units_base import SampleUnitFilterSet, SampleUnitSerializer


class QuadratCollectionSerializer(SampleUnitSerializer):
    class Meta:
        model = QuadratCollection
        exclude = []
        extra_kwargs = {"quadrat_size": {"error_messages": {"null": "Quadrat size is required"}}}
        extra_kwargs.update(SampleUnitSerializer.extra_kwargs)


class QuadratCollectionFilterSet(SampleUnitFilterSet):
    class Meta:
        model = QuadratCollection
        exclude = []


class QuadratCollectionViewSet(BaseProjectApiViewSet):
    serializer_class = QuadratCollectionSerializer
    queryset = QuadratCollection.objects.all()
    filterset_class = QuadratCollectionFilterSet
