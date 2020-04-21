from rest_framework.decorators import action
from .base import (
    BaseAPIFilterSet,
    BaseProjectApiViewSet,
    BaseAPISerializer,
)
from .mixins import ProtectedResourceMixin
from ..models import Site
from ..report_serializer import *
from . import fieldreport


class PSiteSerializer(BaseAPISerializer):
    class Meta:
        geo_field = "location"
        model = Site
        exclude = []


class PSiteReportSerializer(ReportSerializer):
    fields = [
        ReportField("country__name", "Country"),
        ReportField("name", "Name"),
        ReportField("location", "Latitude", to_latitude),
        ReportField("location", "Longitude", to_longitude),
        ReportField("reef_type__name", "Reef type"),
        ReportField("reef_zone__name", "Reef zone"),
        ReportField("exposure__name", "Reef exposure"),
        ReportField("notes", "Notes"),
    ]

    class Meta:
        model = Site


class PSiteFilterSet(BaseAPIFilterSet):
    class Meta:
        model = Site
        fields = ["country", "reef_type", "reef_zone", "exposure"]


class PSiteViewSet(ProtectedResourceMixin, BaseProjectApiViewSet):
    model_display_name = "Site"
    serializer_class = PSiteSerializer
    queryset = Site.objects.all()
    project_lookup = "project"
    filter_class = PSiteFilterSet
    search_fields = ["name"]

    @action(detail=False, methods=["get"])
    def fieldreport(self, request, *args, **kwargs):
        return fieldreport(
            self,
            request,
            *args,
            model_cls=Site,
            serializer_class=PSiteReportSerializer,
            fk="id",
            order_by=("Country", "Name", ),
            **kwargs
        )
