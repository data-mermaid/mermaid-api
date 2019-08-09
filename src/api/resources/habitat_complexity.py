from rest_framework import serializers
from .base import BaseAPIFilterSet, BaseProjectApiViewSet, BaseAPISerializer
from ..models import HabitatComplexity


class HabitatComplexitySerializer(BaseAPISerializer):
    interval_size = serializers.DecimalField(max_digits=4,
                                             decimal_places=2,
                                             coerce_to_string=False,
                                             error_messages={"null": "Interval size is required"})

    class Meta:
        model = HabitatComplexity
        exclude = []


class HabitatComplexityFilterSet(BaseAPIFilterSet):

    class Meta:
        model = HabitatComplexity
        fields = ['transect', 'transect__sample_event', ]


class HabitatComplexityViewSet(BaseProjectApiViewSet):
    serializer_class = HabitatComplexitySerializer
    queryset = HabitatComplexity.objects.all()
    filter_class = HabitatComplexityFilterSet
