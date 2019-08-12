from .base import (
    BaseAPIFilterSet,
    BaseProjectApiViewSet,
    BaseAPISerializer,
)
from ..models import BenthicLIT


class BenthicLITSerializer(BaseAPISerializer):

    class Meta:
        model = BenthicLIT
        exclude = []


class BenthicLITFilterSet(BaseAPIFilterSet):

    class Meta:
        model = BenthicLIT
        fields = ['transect', 'transect__sample_event', ]


class BenthicLITViewSet(BaseProjectApiViewSet):
    serializer_class = BenthicLITSerializer
    queryset = BenthicLIT.objects.all()
    filter_class = BenthicLITFilterSet
