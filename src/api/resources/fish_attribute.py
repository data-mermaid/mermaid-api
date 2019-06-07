from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from rest_framework import permissions, serializers
from base import BaseAttributeApiViewSet, BaseAPISerializer
from ..models import FishAttributeView
from base import (
    StandardResultPagination,
    BaseAPIFilterSet
)


class FishAttributeSerializer(BaseAPISerializer):
    biomass_constant_a = serializers.DecimalField(max_digits=7, decimal_places=6, coerce_to_string=False)
    biomass_constant_b = serializers.DecimalField(max_digits=7, decimal_places=6, coerce_to_string=False)
    biomass_constant_c = serializers.DecimalField(max_digits=7, decimal_places=6, coerce_to_string=False)

    class Meta:
        model = FishAttributeView
        exclude = []


class FishAttributeExtendedSerializer(FishAttributeSerializer):
    taxonomic_rank = serializers.ReadOnlyField()

    class Meta:
        model = FishAttributeView
        exclude = ['updated_on', 'created_on', 'updated_by', 'id']

    def get_name(self, obj):
        return obj.__unicode__()


class FishAttributePermission(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.method in permissions.SAFE_METHODS


class FishAttributeFilterSet(BaseAPIFilterSet):

    class Meta:
        model = FishAttributeView
        fields = ['updated_on']


class FishAttributeViewSet(BaseAttributeApiViewSet):
    serializer_class = FishAttributeSerializer
    queryset = FishAttributeView.objects.all().order_by('name')
    permission_classes = [FishAttributePermission, ]
    pagination_class = StandardResultPagination
    filter_class = FishAttributeFilterSet

    @method_decorator(cache_page(60*60))
    def list(self, request, *args, **kwargs):
        return super(FishAttributeViewSet, self).list(request, *args, **kwargs)
