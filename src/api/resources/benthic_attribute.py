from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from rest_framework import serializers
from django_filters import ModelMultipleChoiceFilter
from .base import BaseAPIFilterSet, NullableUUIDFilter, BaseAPISerializer, BaseAttributeApiViewSet
from .mixins import CreateOrUpdateSerializerMixin
from ..models import BenthicAttribute, Region


class BenthicAttributeSerializer(CreateOrUpdateSerializerMixin, BaseAPISerializer):
    status = serializers.ReadOnlyField()

    class Meta:
        model = BenthicAttribute
        exclude = []


class BenthicAttributeFilterSet(BaseAPIFilterSet):
    parent = NullableUUIDFilter(field_name='parent')
    life_history = NullableUUIDFilter(field_name='life_history')
    regions = ModelMultipleChoiceFilter(queryset=Region.objects.all())

    class Meta:
        model = BenthicAttribute
        fields = ['parent', 'life_history', 'regions', ]


class BenthicAttributeViewSet(BaseAttributeApiViewSet):
    serializer_class = BenthicAttributeSerializer
    queryset = BenthicAttribute.objects.select_related().prefetch_related('regions')
    filter_class = BenthicAttributeFilterSet
    search_fields = ['name', ]

    def list(self, request, *args, **kwargs):
        return super(BenthicAttributeViewSet, self).list(request, *args, **kwargs)
