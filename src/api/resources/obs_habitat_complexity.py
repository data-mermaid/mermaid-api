from .base import (
    BaseAPIFilterSet,
    BaseProjectApiViewSet,
    BaseAPISerializer,
)
from ..models import ObsHabitatComplexity


class ObsHabitatComplexitySerializer(BaseAPISerializer):

    class Meta:
        model = ObsHabitatComplexity
        exclude = []


class ObsHabitatComplexityFilterSet(BaseAPIFilterSet):

    class Meta:
        model = ObsHabitatComplexity
        fields = ['habitatcomplexity', 'habitatcomplexity__transect', 'habitatcomplexity__transect__sample_event',
                  'score', 'include', ]


class ObsHabitatComplexityViewSet(BaseProjectApiViewSet):
    serializer_class = ObsHabitatComplexitySerializer
    queryset = ObsHabitatComplexity.objects.prefetch_related(ObsHabitatComplexity.project_lookup)
    filter_class = ObsHabitatComplexityFilterSet
