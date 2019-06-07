import django_filters
from rest_framework import serializers

from base import BaseAPIFilterSet, BaseAPISerializer, BaseProjectApiViewSet

from ..models import ObsBeltFish


class ObsBeltFishSerializer(BaseAPISerializer):
    size = serializers.DecimalField(
        max_digits=5, decimal_places=1, coerce_to_string=False
    )

    class Meta:
        model = ObsBeltFish
        exclude = []
        extra_kwargs = {
            "fish_attribute": {
                "error_messages": {"does_not_exist": "Fish attribute with id \"{pk_value}\", does not exist."}
            }
        }


class ObsBeltFishFilterSet(BaseAPIFilterSet):
    size = django_filters.NumericRangeFilter(name="size")
    count = django_filters.NumericRangeFilter(name="count")

    class Meta:
        model = ObsBeltFish
        fields = [
            "beltfish",
            "beltfish__transect",
            "beltfish__transect__sample_event",
            "fish_attribute",
            "size_bin",
            "include",
            "size",
            "count",
        ]


class ObsBeltFishViewSet(BaseProjectApiViewSet):
    serializer_class = ObsBeltFishSerializer
    queryset = ObsBeltFish.objects.prefetch_related(ObsBeltFish.project_lookup)
    filter_class = ObsBeltFishFilterSet
