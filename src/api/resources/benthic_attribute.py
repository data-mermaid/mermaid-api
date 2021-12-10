from django.db.models import Prefetch
from django_filters import BaseInFilter
from rest_framework import serializers
from .base import (
    BaseAPIFilterSet,
    NullableUUIDFilter,
    BaseAPISerializer,
    BaseAttributeApiViewSet,
)
from .mixins import CreateOrUpdateSerializerMixin
from ..models import BenthicAttribute, Region


class BenthicAttributeSerializer(CreateOrUpdateSerializerMixin, BaseAPISerializer):
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
    queryset = BenthicAttribute.objects.select_related().prefetch_related(Prefetch("regions", queryset=Region.objects.all().only("id")))
    filterset_class = BenthicAttributeFilterSet
    search_fields = [
        "name",
    ]

    def filter_queryset(self, queryset):
        qs = super().filter_queryset(queryset)

        if "regions" in self.request.query_params:
            qs = qs.distinct()

        return qs
