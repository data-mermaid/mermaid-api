from .base import BaseAPIFilterSet, BaseAPISerializer, BaseProjectApiViewSet

from ..models import ObsColoniesBleached


class ObsColoniesBleachedSerializer(BaseAPISerializer):
    class Meta:
        model = ObsColoniesBleached
        exclude = []
        extra_kwargs = {
            "attribute": {
                "error_messages": {
                    "does_not_exist": 'Benthic attribute with id "{pk_value}", does not exist.'
                }
            }
        }


class ObsColoniesBleachedFilterSet(BaseAPIFilterSet):
    class Meta:
        model = ObsColoniesBleached
        exclude = ["data"]


class ObsColoniesBleachedViewSet(BaseProjectApiViewSet):
    serializer_class = ObsColoniesBleachedSerializer
    queryset = ObsColoniesBleached.objects.prefetch_related(
        ObsColoniesBleached.project_lookup
    )
    filterset_class = ObsColoniesBleachedFilterSet
