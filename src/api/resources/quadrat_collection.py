from rest_framework import serializers

from ..models import QuadratCollection
from .base import BaseProjectApiViewSet
from .sample_units_base import SampleUnitFilterSet, SampleUnitSerializer


class QuadratCollectionSerializer(SampleUnitSerializer):
    quadrat_size = serializers.DecimalField(
        max_digits=6,
        decimal_places=2,
        coerce_to_string=False,
        min_value=0,
        error_messages={"null": "Quadrat size is required"},
    )

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
