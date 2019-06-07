from base import BaseAPIFilterSet, BaseAPISerializer, BaseProjectApiViewSet
from ..models import ObsBenthicPIT


class ObsBenthicPITSerializer(BaseAPISerializer):

    class Meta:
        model = ObsBenthicPIT
        exclude = []
        extra_kwargs = {
            "attribute": {
                "error_messages": {"does_not_exist": "Benthic attribute with id \"{pk_value}\", does not exist."}
            }
        }


class ObsBenthicPITFilterSet(BaseAPIFilterSet):

    class Meta:
        model = ObsBenthicPIT
        fields = ['benthicpit', 'benthicpit__transect', 'benthicpit__transect__sample_event', 'attribute',
                  'include', ]


class ObsBenthicPITViewSet(BaseProjectApiViewSet):
    serializer_class = ObsBenthicPITSerializer
    queryset = ObsBenthicPIT.objects.prefetch_related(ObsBenthicPIT.project_lookup)
    filter_class = ObsBenthicPITFilterSet
