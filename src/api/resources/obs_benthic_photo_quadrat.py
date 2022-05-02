import django_filters

from ..models import ObsBenthicPhotoQuadrat
from .base import BaseAPIFilterSet, BaseAPISerializer, BaseProjectApiViewSet


class ObsBenthicPhotoQuadratSerializer(BaseAPISerializer):
    class Meta:
        model = ObsBenthicPhotoQuadrat
        exclude = []
        extra_kwargs = {
            "attribute": {
                "error_messages": {
                    "does_not_exist": 'Benthic attribute with id "{pk_value}", does not exist.'
                }
            }
        }


class ObsBenthicPhotoQuadratFilterSet(BaseAPIFilterSet):
    length = django_filters.RangeFilter(field_name="length")

    class Meta:
        model = ObsBenthicPhotoQuadrat
        fields = [
            # "benthicphotoquadrattransect",
            # "benthicphotoquadrattransect__quadrat_transect",
            # "benthicphotoquadrattransect__quadrat_transect__sample_event",
            "attribute",
            "growth_form",
            # "include",
            "length",
        ]


class ObsBenthicPhotoQuadratViewSet(BaseProjectApiViewSet):
    serializer_class = ObsBenthicPhotoQuadratSerializer
    queryset = ObsBenthicPhotoQuadrat.objects.prefetch_related(
        ObsBenthicPhotoQuadrat.project_lookup
    )
    filter_class = ObsBenthicPhotoQuadratFilterSet
