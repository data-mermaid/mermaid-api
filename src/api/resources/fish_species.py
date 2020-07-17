from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from rest_framework import serializers
from .base import BaseAPIFilterSet, BaseAttributeApiViewSet, BaseAPISerializer
from ..models import FishSpecies


class FishSpeciesSerializer(BaseAPISerializer):
    status = serializers.ReadOnlyField()
    display_name = serializers.SerializerMethodField()
    biomass_constant_a = serializers.DecimalField(max_digits=7,
                                                  decimal_places=6,
                                                  coerce_to_string=False,
                                                  required=False,
                                                  allow_null=True)
    biomass_constant_b = serializers.DecimalField(max_digits=7,
                                                  decimal_places=6,
                                                  coerce_to_string=False,
                                                  required=False,
                                                  allow_null=True)
    biomass_constant_c = serializers.DecimalField(max_digits=7,
                                                  decimal_places=6,
                                                  coerce_to_string=False,
                                                  required=False,
                                                  allow_null=True)
    climate_score = serializers.DecimalField(max_digits=10,
                                             decimal_places=9,
                                             coerce_to_string=False,
                                             required=False,
                                             allow_null=True)

    class Meta:
        model = FishSpecies
        exclude = []

    def get_display_name(self, obj):
        return str(obj)


class FishSpeciesFilterSet(BaseAPIFilterSet):

    class Meta:
        model = FishSpecies
        fields = ['genus', 'genus__family', 'status', 'regions', ]


class FishSpeciesViewSet(BaseAttributeApiViewSet):
    serializer_class = FishSpeciesSerializer
    queryset = FishSpecies.objects.select_related().prefetch_related("regions")
    filter_class = FishSpeciesFilterSet
    search_fields = ['name', 'genus__name', ]

    def list(self, request, *args, **kwargs):
        return super(FishSpeciesViewSet, self).list(request, *args, **kwargs)
