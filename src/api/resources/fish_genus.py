from django_filters import BaseInFilter
from rest_framework import serializers

from ..models import FishGenus
from .base import BaseAPIFilterSet, BaseAPISerializer, BaseAttributeApiViewSet


class FishGenusSerializer(BaseAPISerializer):
    status = serializers.ReadOnlyField()
    biomass_constant_a = serializers.ReadOnlyField()
    biomass_constant_b = serializers.ReadOnlyField()
    biomass_constant_c = serializers.ReadOnlyField()
    regions = serializers.ReadOnlyField()

    class Meta:
        model = FishGenus
        exclude = []


class FishGenusFilterSet(BaseAPIFilterSet):
    regions = BaseInFilter(field_name="fishspecies__regions", lookup_expr="in")

    class Meta:
        model = FishGenus
        fields = ["family", "status", "regions"]


class FishGenusViewSet(BaseAttributeApiViewSet):
    serializer_class = FishGenusSerializer
    queryset = FishGenus.objects.select_related()
    filterset_class = FishGenusFilterSet
    search_fields = ["name"]

    def stringify_instance(self, v):
        if v is None:
            return None
        return str(v.pk)

    def filter_queryset(self, queryset):
        qs = super().filter_queryset(queryset)

        if "regions" in self.request.query_params:
            qs = qs.distinct()

        return qs
