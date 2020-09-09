import django_filters
from .base import (
    BaseAPIFilterSet,
    BaseProjectApiViewSet,
    BaseAPISerializer,
)
from ..models import ObsBenthicLIT


class ObsBenthicLITSerializer(BaseAPISerializer):

    class Meta:
        model = ObsBenthicLIT
        exclude = []
        extra_kwargs = {
            "attribute": {
                "error_messages": {"does_not_exist": "Benthic attribute with id \"{pk_value}\", does not exist."}
            }
        }


class ObsBenthicLITFilterSet(BaseAPIFilterSet):
    length = django_filters.RangeFilter(field_name='length')

    class Meta:
        model = ObsBenthicLIT
        fields = ['benthiclit', 'benthiclit__transect', 'benthiclit__transect__sample_event', 'attribute',
                  'include', 'length', ]


class ObsBenthicLITViewSet(BaseProjectApiViewSet):
    serializer_class = ObsBenthicLITSerializer
    queryset = ObsBenthicLIT.objects.prefetch_related(ObsBenthicLIT.project_lookup)
    filter_class = ObsBenthicLITFilterSet
