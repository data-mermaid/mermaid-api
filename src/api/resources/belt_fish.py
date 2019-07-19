from .base import BaseAPIFilterSet, BaseProjectApiViewSet, BaseAPISerializer
from ..models import BeltFish


class BeltFishSerializer(BaseAPISerializer):

    class Meta:
        model = BeltFish
        exclude = []


class BeltFishFilterSet(BaseAPIFilterSet):

    class Meta:
        model = BeltFish
        fields = ['transect', 'transect__sample_event', ]


class BeltFishViewSet(BaseProjectApiViewSet):
    serializer_class = BeltFishSerializer
    queryset = BeltFish.objects.all()
    filter_class = BeltFishFilterSet
