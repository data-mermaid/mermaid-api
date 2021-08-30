import django_filters

from rest_framework.exceptions import ValidationError
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from .base import (
    BaseAPIFilterSet,
    BaseProjectApiViewSet,
    BaseAPISerializer,
    ExtendedSerializer,
    ModelNameReadOnlyField,
)
from .site import SiteExtendedSerializer
from .management import ManagementExtendedSerializer
from ..models import SampleEvent


class SampleEventExtendedSerializer(ExtendedSerializer):
    site = SiteExtendedSerializer()
    management = ManagementExtendedSerializer(exclude=['project'])

    class Meta:
        model = SampleEvent
        exclude = []


class SampleEventSerializer(BaseAPISerializer):

    class Meta:
        model = SampleEvent
        exclude = []
        extra_kwargs = {
            "sample_date": {
                "error_messages": {"null": "Sample date is required"}
            },
            "site": {
                "error_messages": {"null": "Site is required"}
            },
            "management": {
                "error_messages": {"null": "Management is required"}
            },
        }


class SampleEventFilterSet(BaseAPIFilterSet):
    sample_date = django_filters.DateTimeFromToRangeFilter(field_name="sample_date")

    class Meta:
        model = SampleEvent
        fields = ['site', 'management', 'sample_date']


class SampleEventViewSet(BaseProjectApiViewSet):
    serializer_class = SampleEventSerializer
    queryset = SampleEvent.objects.all()
    filter_class = SampleEventFilterSet

    def perform_update(self, serializer):
        serializer.save()
