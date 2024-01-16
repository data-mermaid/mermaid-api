import django_filters

from ..models import FishBeltTransect
from .base import BaseProjectApiViewSet, ModelValReadOnlyField
from .sample_units_base import (
    SampleUnitExtendedSerializer,
    SampleUnitFilterSet,
    SampleUnitSerializer,
)


class FishBeltTransectExtendedSerializer(SampleUnitExtendedSerializer):
    width = ModelValReadOnlyField()

    class Meta:
        model = FishBeltTransect
        exclude = []


class FishBeltTransectSerializer(SampleUnitSerializer):
    class Meta:
        model = FishBeltTransect
        exclude = []
        extra_kwargs = {
            "number": {"error_messages": {"null": "Transect number is required"}},
            "len_surveyed": {"error_messages": {"null": "Transect length surveyed is required"}},
            "width": {"error_messages": {"null": "Width is required"}},
            "size_bin": {"error_messages": {"null": "Fish size bin is required"}},
        }
        extra_kwargs.update(SampleUnitSerializer.extra_kwargs)


class FishBeltTransectFilterSet(SampleUnitFilterSet):
    len_surveyed = django_filters.RangeFilter(field_name="len_surveyed")

    class Meta:
        model = FishBeltTransect
        fields = [
            "beltfish_method",
            "sample_event",
            "len_surveyed",
            "width",
            "depth",
        ] + SampleUnitFilterSet.fields


class FishBeltTransectViewSet(BaseProjectApiViewSet):
    serializer_class = FishBeltTransectSerializer
    queryset = FishBeltTransect.objects.all()
    filterset_class = FishBeltTransectFilterSet
