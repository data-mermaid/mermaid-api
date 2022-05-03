import django_filters
from .base import BaseAPIFilterSet, BaseAPISerializer, BaseProjectApiViewSet
from .sample_units_base import (
    SampleUnitFilterSet,
    SampleUnitSerializer,
)
from ..models import QuadratTransect


class QuadratTransectSerializer(SampleUnitSerializer):
    class Meta:
        model = QuadratTransect
        exclude = []
        extra_kwargs = {
            "quadrat_size": {"error_messages": {"null": "Quadrat size is required"}},
            "num_quadrats": {"error_messages": {"null": "Number of quadrats is required"}},
            "num_points_per_quadrat": {"error_messages": {"null": "Number of points per quadrat is required"}}
        }
        extra_kwargs.update(SampleUnitSerializer.extra_kwargs)


# class QuadratTransectFilterSet(SampleUnitFilterSet):
#     class Meta:
#         model = QuadratTransect
#         exclude = []


# class QuadratTransectViewSet(BaseProjectApiViewSet):
#     serializer_class = QuadratTransectSerializer
#     queryset = QuadratTransect.objects.all()
#     filter_class = QuadratTransectFilterSet
