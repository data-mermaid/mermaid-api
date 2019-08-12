from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from rest_framework import serializers
from .base import BaseAPIFilterSet, BaseAttributeApiViewSet, BaseAPISerializer
from ..models import FishGenus


class FishGenusSerializer(BaseAPISerializer):
    status = serializers.ReadOnlyField()
    biomass_constant_a = serializers.ReadOnlyField()
    biomass_constant_b = serializers.ReadOnlyField()
    biomass_constant_c = serializers.ReadOnlyField()

    class Meta:
        model = FishGenus
        exclude = []


class FishGenusFilterSet(BaseAPIFilterSet):

    class Meta:
        model = FishGenus
        fields = ['family', 'status', ]


class FishGenusViewSet(BaseAttributeApiViewSet):
    serializer_class = FishGenusSerializer
    queryset = FishGenus.objects.select_related()
    filter_class = FishGenusFilterSet
    search_fields = ['name', ]

    @method_decorator(cache_page(60*60))
    def list(self, request, *args, **kwargs):
        return super(FishGenusViewSet, self).list(request, *args, **kwargs)
