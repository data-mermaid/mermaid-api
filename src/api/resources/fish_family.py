from django_filters import BaseInFilter
from rest_framework import serializers

from ..models import FishFamily
from .base import BaseAPIFilterSet, BaseAPISerializer, BaseAttributeApiViewSet


class FishFamilySerializer(BaseAPISerializer):
    status = serializers.ReadOnlyField()
    biomass_constant_a = serializers.ReadOnlyField()
    biomass_constant_b = serializers.ReadOnlyField()
    biomass_constant_c = serializers.ReadOnlyField()
    regions = serializers.ReadOnlyField()

    class Meta:
        model = FishFamily
        exclude = []


class FishFamilyFilterSet(BaseAPIFilterSet):
    regions = BaseInFilter(field_name="fishgenus__fishspecies__regions", lookup_expr="in")

    class Meta:
        model = FishFamily
        fields = ["status", "regions"]


class FishFamilyViewSet(BaseAttributeApiViewSet):
    serializer_class = FishFamilySerializer
    queryset = FishFamily.objects.select_related()
    filterset_class = FishFamilyFilterSet
    search_fields = ["name"]

    def filter_queryset(self, queryset):
        qs = super().filter_queryset(queryset)

        if "regions" in self.request.query_params:
            qs = qs.distinct()

        return qs
