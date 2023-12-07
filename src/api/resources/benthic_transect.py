import django_filters

from ..models import BenthicTransect
from .base import BaseAPIFilterSet, BaseAPISerializer, BaseProjectApiViewSet
from .sample_units_base import SampleUnitFilterSet, SampleUnitSerializer


class BenthicTransectSerializer(SampleUnitSerializer):
    class Meta:
        model = BenthicTransect
        exclude = []
        extra_kwargs = {
            "len_surveyed": {"error_messages": {"null": "Transect length surveyed is required"}},
            "number": {"error_messages": {"null": "Transect Number is required"}},
        }
        extra_kwargs.update(SampleUnitSerializer.extra_kwargs)


class BenthicTransectFilterSet(SampleUnitFilterSet):
    len_surveyed = django_filters.RangeFilter(field_name="len_surveyed")

    class Meta:
        model = BenthicTransect
        fields = [
            "benthiclit_method",
            "benthicpit_method",
            "habitatcomplexity_method",
            "sample_event",
            "len_surveyed",
        ] + SampleUnitFilterSet.fields


class BenthicTransectViewSet(BaseProjectApiViewSet):
    serializer_class = BenthicTransectSerializer
    queryset = BenthicTransect.objects.all()
    filterset_class = BenthicTransectFilterSet
