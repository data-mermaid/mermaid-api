from .base import BaseAPIFilterSet, BaseAPISerializer, BaseProjectApiViewSet

from ..models import ObsQuadratBenthicPercent


class ObsQuadratBenthicPercentSerializer(BaseAPISerializer):
    class Meta:
        model = ObsQuadratBenthicPercent
        exclude = []
        extra_kwargs = {}


class ObsQuadratBenthicPercentFilterSet(BaseAPIFilterSet):
    class Meta:
        model = ObsQuadratBenthicPercent
        exclude = ["data"]


class ObsQuadratBenthicPercentViewSet(BaseProjectApiViewSet):
    serializer_class = ObsQuadratBenthicPercentSerializer
    queryset = ObsQuadratBenthicPercent.objects.prefetch_related(
        ObsQuadratBenthicPercent.project_lookup
    )
    filter_class = ObsQuadratBenthicPercentFilterSet
