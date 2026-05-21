import django_filters

from ..models import InvertBeltTransect
from .base import BaseProjectApiViewSet, ModelValReadOnlyField
from .sample_units_base import (
    SampleUnitExtendedSerializer,
    SampleUnitFilterSet,
    SampleUnitSerializer,
)


class InvertBeltTransectExtendedSerializer(SampleUnitExtendedSerializer):
    width = ModelValReadOnlyField()

    class Meta:
        model = InvertBeltTransect
        exclude = []


class InvertBeltTransectSerializer(SampleUnitSerializer):
    class Meta:
        model = InvertBeltTransect
        exclude = []
        extra_kwargs = {
            **SampleUnitSerializer.extra_kwargs,
            "number": {"error_messages": {"null": "Transect number is required"}},
            "len_surveyed": {"error_messages": {"null": "Transect length surveyed is required"}},
            "width": {"error_messages": {"null": "Width is required"}},
        }


class InvertBeltTransectFilterSet(SampleUnitFilterSet):
    len_surveyed = django_filters.RangeFilter(field_name="len_surveyed")

    class Meta:
        model = InvertBeltTransect
        fields = [
            "beltinvert_method",
            "sample_event",
            "len_surveyed",
            "width",
            "size_bin",
            "depth",
        ] + SampleUnitFilterSet.fields


class InvertBeltTransectViewSet(BaseProjectApiViewSet):
    http_method_names = ["get", "post", "delete", "head", "options"]
    serializer_class = InvertBeltTransectSerializer
    queryset = InvertBeltTransect.objects.order_by("id")
    filterset_class = InvertBeltTransectFilterSet
