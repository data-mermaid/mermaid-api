import django_filters

from ..models import SampleEvent
from .base import (
    BaseAPIFilterSet,
    BaseAPISerializer,
    BaseProjectApiViewSet,
    ExtendedSerializer,
)
from .management import ManagementExtendedSerializer
from .site import SiteExtendedSerializer


class SampleEventExtendedSerializer(ExtendedSerializer):
    site = SiteExtendedSerializer()
    management = ManagementExtendedSerializer(exclude=["project"])

    class Meta:
        model = SampleEvent
        exclude = []


class SampleEventSerializer(BaseAPISerializer):
    class Meta:
        model = SampleEvent
        exclude = [
            "current",
            "depth",
            "relative_depth",
            "sample_time",
            "tide",
            "visibility",
        ]
        extra_kwargs = {
            "sample_date": {"error_messages": {"null": "Sample date is required"}},
            "site": {"error_messages": {"null": "Site is required"}},
            "management": {"error_messages": {"null": "Management is required"}},
        }


class SampleEventFilterSet(BaseAPIFilterSet):
    sample_date = django_filters.DateTimeFromToRangeFilter(field_name="sample_date")

    class Meta:
        model = SampleEvent
        fields = ["site", "management", "sample_date"]


class SampleEventViewSet(BaseProjectApiViewSet):
    serializer_class = SampleEventSerializer
    queryset = SampleEvent.objects.all()
    filter_class = SampleEventFilterSet


    def perform_update(self, serializer):
        serializer.save()
