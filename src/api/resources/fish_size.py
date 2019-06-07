from base import BaseApiViewSet, BaseAPISerializer, BaseAPIFilterSet
from ..models import FishSize
from ..permissions import UnauthenticatedReadOnlyPermission


class FishSizeSerializer(BaseAPISerializer):

    class Meta:
        model = FishSize
        exclude = []


class FishSizeFilterSet(BaseAPIFilterSet):

    class Meta:
        model = FishSize
        fields = ['val', ]


class FishSizeViewSet(BaseApiViewSet):
    permission_classes = [UnauthenticatedReadOnlyPermission]
    method_authentication_classes = {
        "GET": []
    }
    filter_class = FishSizeFilterSet

    serializer_class = FishSizeSerializer
    queryset = FishSize.objects.all().order_by('name')
