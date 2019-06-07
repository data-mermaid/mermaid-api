from datetime import datetime
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponseBadRequest, StreamingHttpResponse
from django.utils.text import get_valid_filename
from rest_framework.decorators import list_route
from rest_framework.serializers import DecimalField
import django_filters
from base import (
    BaseAPIFilterSet,
    BaseProjectApiViewSet,
    BaseAPISerializer,
    NullableUUIDFilter,
)
from mixins import ProtectedResourceMixin
from .management import get_rules
from ..models import Management, Project
from ..reports import RawCSVReport
from ..report_serializer import *


class PManagementSerializer(BaseAPISerializer):
    size = DecimalField(max_digits=12,
                        decimal_places=3,
                        coerce_to_string=False,
                        required=False,
                        allow_null=True)

    class Meta:
        model = Management
        exclude = []


def to_governance(field, row, serializer_instance):
    parties = ""
    project_pk = row.get("project_id")
    management_id = row.get("id")
    lookup = serializer_instance.serializer_cache.get(
        "management_parties-{}".format(project_pk)
    )
    if lookup:
        parties = lookup.get(str(management_id))
    else:
        management = Management.objects.get_or_none(id=management_id)
        if management is not None:
            mps = management.parties.all().iterator()
            parties = ",".join([mp.name for mp in mps])
    return parties


def to_management_rules(field, row, serializer_instance):
    project_pk = row.get("project_id")
    management_id = row.get("id")
    lookup = serializer_instance.serializer_cache.get(
        "management_rules-{}".format(project_pk)
    )
    if lookup:
        return lookup.get(str(management_id))

    return get_rules(Management.objects.get_or_none(id=management_id))


class PManagementReportSerializer(ReportSerializer):
    fields = [
        ReportField("name", "Name"),
        ReportField("name_secondary", "Secondary name"),
        ReportField("est_year", "Year established"),
        ReportField("size", "Size", to_float),
        ReportMethodField("Governance", to_governance),
        ReportField("compliance__name", "Estimated compliance"),
        ReportMethodField("Rules", to_management_rules),
        ReportField("notes", "Notes"),
    ]

    non_field_columns = (
        "id",
        "project_id",
    )

    class Meta:
        model = Management

    def preserialize(self, queryset=None):
        self.serializer_cache = dict()
        try:
            project_pk = queryset.values_list("project_id", flat=True)[0]
        except ObjectDoesNotExist:
            return

        management_parties_lookup = dict()
        management_rules_lookup = dict()
        for m in Management.objects.filter(project_id=project_pk):
            parties = m.parties.all().order_by("name").values_list("name", flat=True)
            management_parties_lookup[str(m.id)] = ",".join(parties)
            management_rules_lookup[str(m.id)] = get_rules(m)

        if len(management_parties_lookup.keys()) > 0:
            self.serializer_cache[
                "management_parties-{}".format(project_pk)
            ] = management_parties_lookup
            self.serializer_cache[
                "management_rules-{}".format(project_pk)
            ] = management_rules_lookup


class PManagementFilterSet(BaseAPIFilterSet):
    predecessor = NullableUUIDFilter(name='predecessor')
    compliance = NullableUUIDFilter(name='compliance')
    est_year = django_filters.NumericRangeFilter(name='est_year')

    class Meta:
        model = Management
        fields = ['predecessor', 'parties', 'compliance', 'est_year', 'no_take', 'periodic_closure',
                  'open_access', 'size_limits', 'gear_restriction', 'species_restriction', ]


class PManagementViewSet(ProtectedResourceMixin, BaseProjectApiViewSet):
    model_display_name = "Management Regime"
    serializer_class = PManagementSerializer
    queryset = Management.objects.all()
    filter_class = PManagementFilterSet
    search_fields = ['name', 'name_secondary', ]

    @list_route(methods=["get"])
    def fieldreport(self, request, *args, **kwargs):
        try:
            project = Project.objects.get(pk=kwargs['project_pk'])
        except ObjectDoesNotExist:
            return HttpResponseBadRequest('Project doesn\'t exist')
        self.limit_to_project(self, request, *args, **kwargs)

        report = RawCSVReport()
        stream = report.stream(
            self.get_queryset(),
            serializer_class=PManagementReportSerializer)
        response = StreamingHttpResponse(stream, content_type='text/csv')
        ts = datetime.utcnow().strftime("%Y%m%d")
        projname = get_valid_filename(project.name)[:100]
        response['Content-Disposition'] = \
            'attachment; filename="management_regimes-%s-%s.csv"' % (projname, ts)
        return response
