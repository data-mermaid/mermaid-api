import django_filters

from ..models import QuadratTransect
from .base import BaseAPIFilterSet, BaseAPISerializer, BaseProjectApiViewSet
from .sample_units_base import SampleUnitFilterSet, SampleUnitSerializer


class QuadratTransectSerializer(SampleUnitSerializer):
    class Meta:
        model = QuadratTransect
        exclude = []
        extra_kwargs = {
            "quadrat_size": {"error_messages": {"null": "Quadrat size is required"}},
            "num_quadrats": {"error_messages": {"null": "Number of quadrats is required"}},
            "num_points_per_quadrat": {
                "error_messages": {"null": "Number of points per quadrat is required"}
            },
            "len_surveyed": {"error_messages": {"null": "Transect length surveyed is required"}},
            "number": {"error_messages": {"null": "Transect Number is required"}},
        }
        extra_kwargs.update(SampleUnitSerializer.extra_kwargs)


# class QuadratTransectFilterSet(SampleUnitFilterSet):
#     class Meta:
#         model = QuadratTransect
#         exclude = []


# class QuadratTransectViewSet(BaseProjectApiViewSet):
#     serializer_class = QuadratTransectSerializer
#     queryset = QuadratTransect.objects.all()
#     filterset_class = QuadratTransectFilterSet
