
from rest_framework.validators import UniqueTogetherValidator

from .base import BaseAPIFilterSet, BaseAPISerializer, BaseProjectApiViewSet
from ..models import ObsQuadratBenthicPercent


class ObsQuadratBenthicPercentSerializer(BaseAPISerializer):
    class Meta:
        model = ObsQuadratBenthicPercent
        exclude = []
        extra_kwargs = {
            "quadrat_number": {
                "error_messages": {
                    "null": "Quadrat number is required"
                }
            }
        }
        validators = [
            UniqueTogetherValidator(
                queryset=ObsQuadratBenthicPercent.objects.all(),
                fields=["bleachingquadratcollection", "quadrat_number"],
                message="Duplicate quadrat numbers"
            )
        ]


class ObsQuadratBenthicPercentFilterSet(BaseAPIFilterSet):
    class Meta:
        model = ObsQuadratBenthicPercent
        exclude = ["data"]


class ObsQuadratBenthicPercentViewSet(BaseProjectApiViewSet):
    serializer_class = ObsQuadratBenthicPercentSerializer
    queryset = ObsQuadratBenthicPercent.objects.prefetch_related(
        ObsQuadratBenthicPercent.project_lookup
    )
    filterset_class = ObsQuadratBenthicPercentFilterSet
