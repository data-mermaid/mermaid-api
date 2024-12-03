from django.db.models import F, Value
from django.db.models.functions import Concat
from django_filters import BaseInFilter
from rest_framework import serializers

from ..models import FishSpecies
from .base import (
    ArrayAggExt,
    BaseAPIFilterSet,
    BaseAPISerializer,
    BaseAttributeApiViewSet,
    M2MSerializerMixin,
)
from .mixins import CreateOrUpdateSerializerMixin


class FishSpeciesSerializer(M2MSerializerMixin, CreateOrUpdateSerializerMixin, BaseAPISerializer):
    m2mfields = ["regions"]
    status = serializers.ReadOnlyField()
    display_name = serializers.SerializerMethodField()
    biomass_constant_a = serializers.DecimalField(
        max_digits=7,
        decimal_places=6,
        coerce_to_string=False,
        required=False,
        allow_null=True,
    )
    biomass_constant_b = serializers.DecimalField(
        max_digits=7,
        decimal_places=6,
        coerce_to_string=False,
        required=False,
        allow_null=True,
    )
    biomass_constant_c = serializers.DecimalField(
        max_digits=7,
        decimal_places=6,
        coerce_to_string=False,
        required=False,
        allow_null=True,
    )
    vulnerability = serializers.DecimalField(
        max_digits=4,
        decimal_places=2,
        coerce_to_string=False,
        required=False,
        allow_null=True,
        min_value=0,
        max_value=100,
    )
    max_length = serializers.DecimalField(
        max_digits=6,
        decimal_places=2,
        coerce_to_string=False,
        required=False,
        allow_null=True,
        min_value=1,
        max_value=2000,
    )
    trophic_level = serializers.DecimalField(
        max_digits=3,
        decimal_places=2,
        coerce_to_string=False,
        required=False,
        allow_null=True,
        min_value=1,
        max_value=5,
    )
    climate_score = serializers.DecimalField(
        max_digits=10,
        decimal_places=9,
        coerce_to_string=False,
        required=False,
        allow_null=True,
        min_value=0,
        max_value=1,
    )

    class Meta:
        model = FishSpecies
        exclude = []

    def get_display_name(self, obj):
        # Can't rely on queryset when POSTing
        if hasattr(obj, "display_name"):
            return obj.display_name
        return f"{obj.genus.name} {obj.name}"


class FishSpeciesFilterSet(BaseAPIFilterSet):
    regions = BaseInFilter(field_name="regions", lookup_expr="in")

    class Meta:
        model = FishSpecies
        fields = [
            "genus",
            "genus__family",
            "status",
            "regions",
        ]


class FishSpeciesViewSet(BaseAttributeApiViewSet):
    serializer_class = FishSpeciesSerializer
    queryset = (
        FishSpecies.objects.select_related()
        .annotate(
            regions_=ArrayAggExt("regions"),
            display_name=Concat(F("genus__name"), Value(" "), F("name")),
        )
        .order_by("genus", "name")
    )

    filterset_class = FishSpeciesFilterSet
    search_fields = [
        "name",
        "genus__name",
    ]

    def filter_queryset(self, queryset):
        qs = super().filter_queryset(queryset)

        # Need work around because using qs.distinct("id") is causing an error because
        # of the extra "display_name" that is added to the queryset
        if "regions" in self.request.query_params and "," in self.request.query_params["regions"]:
            ids = qs.values_list("id", flat=True).distinct()
            qs = self.get_queryset().filter(id__in=ids)

        return qs
