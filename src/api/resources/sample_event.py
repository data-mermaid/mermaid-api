import django_filters

from rest_framework.exceptions import ValidationError
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from base import (
    BaseAPIFilterSet,
    BaseProjectApiViewSet,
    BaseAPISerializer,
    ExtendedSerializer,
    ModelNameReadOnlyField,
)
from site import SiteExtendedSerializer
from management import ManagementExtendedSerializer
from ..models import SampleEvent


class SampleEventExtendedSerializer(ExtendedSerializer):
    site = SiteExtendedSerializer()
    management = ManagementExtendedSerializer(exclude=['project'])
    visibility = ModelNameReadOnlyField()
    relative_depth = ModelNameReadOnlyField()
    tide = ModelNameReadOnlyField()
    current = ModelNameReadOnlyField()

    class Meta:
        model = SampleEvent
        exclude = []


class SampleEventSerializer(BaseAPISerializer):
    depth = serializers.DecimalField(max_digits=3,
                                     decimal_places=1,
                                     coerce_to_string=False,
                                     error_messages={"null": "Depth is required"})

    class Meta:
        model = SampleEvent
        exclude = []
        extra_kwargs = {
            "sample_date": {
                "error_messages": {"null": "Sample date is required"}
            },
            "sample_time": {
                "error_messages": {"null": "Sample time is required"}
            },
            "site": {
                "error_messages": {"null": "Site is required"}
            },
            "management": {
                "error_messages": {"null": "Management is required"}
            },
        }


class SampleEventFilterSet(BaseAPIFilterSet):
    sample_date = django_filters.DateTimeFromToRangeFilter(name='sample_date')
    depth = django_filters.NumericRangeFilter(name='depth')

    class Meta:
        model = SampleEvent
        fields = ['site', 'management', 'sample_date', 'sample_time', 'depth', 'visibility', 'current',
                  'relative_depth', 'tide', ]


class SampleEventViewSet(BaseProjectApiViewSet):
    serializer_class = SampleEventSerializer
    queryset = SampleEvent.objects.all()
    filter_class = SampleEventFilterSet
