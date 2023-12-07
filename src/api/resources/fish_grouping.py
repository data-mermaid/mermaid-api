from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from rest_framework import serializers

from ..models import FishGrouping
from .base import BaseAPIFilterSet, BaseAPISerializer, BaseAttributeApiViewSet


class FishGroupingSerializer(BaseAPISerializer):
    status = serializers.ReadOnlyField()
    biomass_constant_a = serializers.ReadOnlyField()
    biomass_constant_b = serializers.ReadOnlyField()
    biomass_constant_c = serializers.ReadOnlyField()
    fish_attributes = serializers.SerializerMethodField()

    class Meta:
        model = FishGrouping
        exclude = []

    def get_fish_attributes(self, obj):
        return [a.attribute_id for a in obj.attribute_grouping.all()]


class FishGroupingFilterSet(BaseAPIFilterSet):
    class Meta:
        model = FishGrouping
        fields = ["status"]


class FishGroupingViewSet(BaseAttributeApiViewSet):
    serializer_class = FishGroupingSerializer
    queryset = FishGrouping.objects.select_related().prefetch_related("regions")
    filterset_class = FishGroupingFilterSet
    search_fields = ["name"]

    def list(self, request, *args, **kwargs):
        return super(FishGroupingViewSet, self).list(request, *args, **kwargs)
