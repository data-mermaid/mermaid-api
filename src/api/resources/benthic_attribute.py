from django.db import connection
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
    top_level_category = serializers.SerializerMethodField()

    class Meta:
        model = BenthicAttribute
        exclude = []
    
    def get_top_level_category(self, obj):
        if hasattr(self, "_top_level_category") is False:
            with connection.cursor() as cur:
                cur.execute("""
                    WITH RECURSIVE tree(child, root) AS (
                        SELECT c_1.id,
                            c_1.id
                        FROM benthic_attribute c_1
                            LEFT JOIN benthic_attribute p ON c_1.parent_id = p.id
                        WHERE p.id IS NULL
                        UNION
                        SELECT benthic_attribute.id,
                            tree_1.root
                        FROM tree tree_1
                            JOIN benthic_attribute ON tree_1.child = benthic_attribute.parent_id
                        )
                    SELECT tree.child, tree.root
                    FROM tree
                """)
                self._top_level_category = {str(row[0]): row[1] for row in cur}
        
        return self._top_level_category.get(str(obj.id))



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
