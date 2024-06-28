from django.db import connection
from django.db.models import F, OuterRef, Subquery
from django.db.models.functions import JSONObject
from django_filters import BaseInFilter
from rest_framework import serializers

from ..models import BenthicAttribute, BenthicAttributeGrowthFormLifeHistory
from .base import (
    ArrayAggExt,
    BaseAPIFilterSet,
    BaseAPISerializer,
    BaseAttributeApiViewSet,
    M2MSerializerMixin,
    NullableUUIDFilter,
)
from .mixins import CreateOrUpdateSerializerMixin


class BenthicAttributeSerializer(
    M2MSerializerMixin, CreateOrUpdateSerializerMixin, BaseAPISerializer
):
    m2mfields = ["regions", "life_histories", "growth_form_life_histories"]
    status = serializers.ReadOnlyField()
    top_level_category = serializers.SerializerMethodField()

    class Meta:
        model = BenthicAttribute
        exclude = []

    def get_top_level_category(self, obj):
        if hasattr(self, "_top_level_category") is False:
            with connection.cursor() as cur:
                cur.execute(
                    """
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
                """
                )
                self._top_level_category = {str(row[0]): row[1] for row in cur}

        return self._top_level_category.get(str(obj.id))


class BenthicAttributeFilterSet(BaseAPIFilterSet):
    parent = NullableUUIDFilter(field_name="parent")
    life_history = BaseInFilter(field_name="life_histories", lookup_expr="in")
    region = BaseInFilter(field_name="regions", lookup_expr="in")

    class Meta:
        model = BenthicAttribute
        fields = [
            "parent",
            "life_history",
            "region",
        ]


class BenthicAttributeViewSet(BaseAttributeApiViewSet):
    serializer_class = BenthicAttributeSerializer
    queryset = BenthicAttribute.objects.annotate(
        regions_=Subquery(
            BenthicAttribute.regions.through.objects.filter(benthicattribute_id=OuterRef("pk"))
            .values("benthicattribute_id")
            .annotate(regions_array=ArrayAggExt("region_id"))
            .values("regions_array")
        ),
        life_histories_=Subquery(
            BenthicAttribute.life_histories.through.objects.filter(
                benthicattribute_id=OuterRef("pk")
            )
            .values("benthicattribute_id")
            .annotate(life_histories_array=ArrayAggExt("benthiclifehistory_id"))
            .values("life_histories_array")
        ),
        growth_form_life_histories_=Subquery(
            BenthicAttributeGrowthFormLifeHistory.objects.filter(attribute_id=OuterRef("pk"))
            .annotate(
                gf_lh=JSONObject(growth_form=F("growth_form"), life_history=F("life_history"))
            )
            .values("attribute_id")
            .annotate(gf_lhs_array=ArrayAggExt("gf_lh"))
            .values("gf_lhs_array")
        ),
    ).distinct()
    filterset_class = BenthicAttributeFilterSet
    search_fields = [
        "name",
    ]

    def filter_queryset(self, queryset):
        qs = super().filter_queryset(queryset)

        if "region" in self.request.query_params or "life_history" in self.request.query_params:
            qs = qs.distinct()

        return qs
