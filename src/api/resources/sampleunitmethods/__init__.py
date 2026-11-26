from django.http import HttpResponseBadRequest
from rest_framework.decorators import action
from rest_framework_gis.pagination import GeoJsonPagination

from ...auth_backends import AnonymousJWTAuthentication
from ...models import Project
from ...permissions import (
    ObjectDoesNotExist,
    ProjectDataReadOnlyPermission,
    ProjectPublicPermission,
    ProjectPublicSummaryPermission,
)
from ...reports import csv_report
from ...resources.base import BaseApiViewSet, BaseProjectApiViewSet
from ...utils import cached, safe_get_valid_filename, truthy
from ...utils.sample_units import consolidate_sample_events, has_duplicate_sample_events


def clean_sample_event_models(data):
    site = data.get("site")
    management = data.get("management")
    sample_date = data.get("sample_date")
    if has_duplicate_sample_events(site, management, sample_date):
        consolidate_sample_events(
            sample_event_data=dict(site=site, management=management, sample_date=sample_date)
        )


class BaseGeoJsonPagination(GeoJsonPagination):
    page_size = 100
    page_size_query_param = "limit"
    max_page_size = 5000


class AggregatedViewMixin(BaseApiViewSet):
    drf_label = ""
    project_policy = None
    serializer_class_geojson = None
    serializer_class_csv = None
    method_authentication_classes = {"GET": [AnonymousJWTAuthentication]}
    http_method_names = ["get"]

    def filter_queryset(self, queryset):
        qs = super().filter_queryset(queryset)
        order_by = getattr(self, "order_by") if hasattr(self, "order_by") else None
        if order_by and qs.query.order_by and qs.query.order_by[0] == "id":
            qs = qs.order_by(*order_by)

        return qs

    @action(detail=False, methods=["get"])
    def json(self, request, *args, **kwargs):  # default, for completeness
        return self.list(request, *args, **kwargs)

    @action(detail=False, methods=["get"])
    def geojson(self, request, *args, **kwargs):
        self.serializer_class = self.serializer_class_geojson
        self.pagination_class = BaseGeoJsonPagination
        return self.list(request, *args, **kwargs)

    @action(detail=False, methods=["get"])
    def csv(self, request, *args, **kwargs):
        is_field_report = truthy(request.query_params.get("field_report"))
        show_display_fields = is_field_report
        include_additional_fields = not is_field_report
        file_name_prefix = f"{self.drf_label}"
        if "file_name_prefix" in kwargs:
            file_name_prefix = kwargs["file_name_prefix"]

        project_id = self.kwargs.get("project_pk")
        if project_id:
            key = cached.make_viewset_cache_key(
                self,
                project_id,
                include_additional_fields=include_additional_fields,
                show_display_fields=show_display_fields,
            )
            if cached.exists(key):
                response = cached.streaming_response(
                    request=request,
                    key=key,
                    file_name=f"{file_name_prefix}.csv",
                    content_type="text/csv",
                    content_encoding="gzip",
                )
                if response:
                    return response

        queryset = self.filter_queryset(self.get_queryset())
        return csv_report.get_csv_response(
            queryset,
            self.serializer_class_csv,
            file_name_prefix=file_name_prefix,
            include_additional_fields=include_additional_fields,
            show_display_fields=show_display_fields,
        )


class BaseProjectMethodView(AggregatedViewMixin, BaseProjectApiViewSet):
    permission_classes = [ProjectDataReadOnlyPermission | ProjectPublicPermission]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.sql_model = getattr(self, "sql_model", None)
        self.use_cached = getattr(self, "use_cached", True)
        if self.sql_model and self.use_cached is False:
            self.model = self.sql_model
            self.filterset_class = self.sql_filterset_class

    @action(detail=False, methods=["get"])
    def csv(self, request, *args, **kwargs):
        try:
            project = Project.objects.get(pk=self.kwargs.get("project_pk"))
        except ObjectDoesNotExist:
            return HttpResponseBadRequest("Project doesn't exist")

        project_name = safe_get_valid_filename(project.name, default=str(project.pk))[:100]
        file_name_prefix = f"{project_name}-{self.drf_label}"

        self.limit_to_project(request, *args, **kwargs)
        kwargs["file_name_prefix"] = file_name_prefix
        return super().csv(request, *args, **kwargs)

    def get_queryset(self):
        project_id = self.kwargs.get("project_pk")
        if self.sql_model and self.use_cached is False:
            return self.model.objects.all().sql_table(project_id=project_id)
        return self.model.objects.filter(project_id=project_id)


class BaseProjectMethodSEView(BaseProjectMethodView):
    """Sample-event-level view for a protocol method. Data is visible under either
    project membership or the protocol's public-summary data sharing policy."""

    permission_classes = [ProjectDataReadOnlyPermission | ProjectPublicSummaryPermission]
