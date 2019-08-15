import django_filters
from .base import (
    BaseAPIFilterSet,
    BaseProjectApiViewSet,
    BaseAPISerializer,
    ExtendedSerializer,
    ModelValReadOnlyField,
)
from ..models import FishBeltTransect


class FishBeltTransectExtendedSerializer(ExtendedSerializer):
    width = ModelValReadOnlyField()

    class Meta:
        model = FishBeltTransect
        exclude = []


class FishBeltTransectSerializer(BaseAPISerializer):

    class Meta:
        model = FishBeltTransect
        exclude = []
        extra_kwargs = {
            "number": {
                "error_messages": {"null": "Transect number is required"}
            },
            "len_surveyed": {
                "error_messages": {"null": "Transect length surveyed is required"}
            },
            "width": {
                "error_messages": {"null": "Width is required"}
            },
            "size_bin": {
                "error_messages": {"null": "Fish size bin is required"}
            },
        }


class FishBeltTransectFilterSet(BaseAPIFilterSet):
    len_surveyed = django_filters.NumericRangeFilter(name='len_surveyed')

    class Meta:
        model = FishBeltTransect
        fields = ['transectbeltfish_method', 'sample_event', 'len_surveyed', 'width', ]


class FishBeltTransectViewSet(BaseProjectApiViewSet):
    serializer_class = FishBeltTransectSerializer
    queryset = FishBeltTransect.objects.all()
    filter_class = FishBeltTransectFilterSet
