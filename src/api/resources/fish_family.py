from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from rest_framework import serializers
from base import BaseAPIFilterSet, BaseAttributeApiViewSet, BaseAPISerializer
from ..models import FishFamily


class FishFamilySerializer(BaseAPISerializer):
    status = serializers.ReadOnlyField()
    biomass_constant_a = serializers.ReadOnlyField()
    biomass_constant_b = serializers.ReadOnlyField()
    biomass_constant_c = serializers.ReadOnlyField()

    class Meta:
        model = FishFamily
        exclude = []


class FishFamilyFilterSet(BaseAPIFilterSet):

    class Meta:
        model = FishFamily
        fields = ['status', ]


class FishFamilyViewSet(BaseAttributeApiViewSet):
    serializer_class = FishFamilySerializer
    queryset = FishFamily.objects.select_related()
    filter_class = FishFamilyFilterSet
    search_fields = ['name', ]

    @method_decorator(cache_page(60*60))
    def list(self, request, *args, **kwargs):
        return super(FishFamilyViewSet, self).list(request, *args, **kwargs)
