from django_filters import BaseInFilter
from rest_framework import serializers
from .base import (
    ArrayAggExt,
    BaseAPIFilterSet,
    NullableUUIDFilter,
    BaseAPISerializer,
    BaseAttributeApiViewSet,
    RegionsSerializerMixin,
)
from .mixins import CreateOrUpdateSerializerMixin
from ..models import BenthicAttribute


class BenthicAttributeSerializer(RegionsSerializerMixin, CreateOrUpdateSerializerMixin, BaseAPISerializer):
    status = serializers.ReadOnlyField()

    class Meta:
        model = BenthicAttribute
        exclude = []


class BenthicAttributeFilterSet(BaseAPIFilterSet):
    parent = NullableUUIDFilter(field_name="parent")
    life_history = NullableUUIDFilter(field_name="life_history")
    regions = BaseInFilter(field_name="regions", lookup_expr="in")

    class Meta:
        model = BenthicAttribute
        fields = [
            "parent",
            "life_history",
            "regions",
        ]


class BenthicAttributeViewSet(BaseAttributeApiViewSet):
    serializer_class = BenthicAttributeSerializer
    queryset = (
        BenthicAttribute.objects.select_related()
        .annotate(regions_=ArrayAggExt("regions"))
    )

    filterset_class = BenthicAttributeFilterSet
    search_fields = [
        "name",
    ]

    def filter_queryset(self, queryset):
        qs = super().filter_queryset(queryset)

        if "regions" in self.request.query_params:
            qs = qs.distinct()

        return qs
