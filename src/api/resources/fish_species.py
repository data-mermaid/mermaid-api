from django_filters import BaseInFilter
from rest_framework import serializers
from .base import BaseAPIFilterSet, BaseAttributeApiViewSet, BaseAPISerializer
from .mixins import CreateOrUpdateSerializerMixin
from ..models import FishSpecies


class FishSpeciesSerializer(CreateOrUpdateSerializerMixin, BaseAPISerializer):
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
    climate_score = serializers.DecimalField(
        max_digits=10,
        decimal_places=9,
        coerce_to_string=False,
        required=False,
        allow_null=True,
    )

    class Meta:
        model = FishSpecies
        exclude = []

    def get_display_name(self, obj):
        return obj.display_name


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
        .extra(select={"display_name": "fish_genus.name || ' ' || fish_species.name"})
        .prefetch_related("regions")
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
        if (
            "regions" in self.request.query_params
            and "," in self.request.query_params["regions"]
        ):
            ids = qs.values_list("id", flat=True).distinct()
            qs = self.get_queryset().filter(id__in=ids)

        return qs
