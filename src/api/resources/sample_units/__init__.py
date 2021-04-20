import uuid

from django.http import HttpResponseBadRequest
from django.utils.text import get_valid_filename
from django.utils.translation import ugettext_lazy as _
from rest_condition import Or
from rest_framework.decorators import action
from rest_framework_gis.pagination import GeoJsonPagination

from ...auth_backends import AnonymousJWTAuthentication
from ...permissions import *
from ...report_serializer import *
from ...reports import csv_report
from ...resources.base import BaseApiViewSet, BaseProjectApiViewSet
from ...utils import truthy
from ...utils.sample_units import consolidate_sample_events, has_duplicate_sample_events


def save_one_to_many(foreign_key, database_records, data, serializer_class, context):
    model_class = serializer_class.Meta.model
    invalid_count = 0
    errors = []

    # Check for deleted records
    # Fetch existing records in database and see
    # if they exist in request.data
    delete_lookup = [o["id"] for o in data if "id" in o and o["id"] is not None]
    for db_record in database_records:
        if db_record.id not in delete_lookup:
            db_record.delete()

    for data_rec in data:
        rec_id = data_rec.get("id")
        fk = data_rec.get(foreign_key[0])
        # If any new records don't have FK, fill it
        if fk is None:
            data_rec[foreign_key[0]] = foreign_key[1]

        # Create new record
        if rec_id is None:
            data_rec["id"] = uuid.uuid4()
            serializer = serializer_class(data=data_rec, context=context)
        else:
            try:
                # Update existing record
                instance = model_class.objects.get(id=rec_id)
                serializer = serializer_class(instance, data=data_rec, context=context)
            except ObjectDoesNotExist:
                # Id provided but new record
                serializer = serializer_class(data=data_rec, context=context)

        if serializer.is_valid() is False:
            errors.append(serializer.errors)
            invalid_count += 1
            continue

        serializer.save()

    return invalid_count == 0, errors


def save_model(data, serializer_class, context):
    model_class = serializer_class.Meta.model
    instance_id = data.get("id")
    instance = model_class.objects.get_or_none(id=instance_id)
    if instance is None:
        return False, [_("Does not exist")]
    else:
        serializer = serializer_class(instance, data=data, context=context)
        if serializer.is_valid() is False:
            return False, serializer.errors

    serializer.save()
    return True, None


def clean_sample_event_models(data):
    site = data.get("site")
    management = data.get("management")
    sample_date = data.get("sample_date")
    if has_duplicate_sample_events(site, management, sample_date):
        consolidate_sample_events(sample_event_data=dict(
            site=site,
            management=management,
            sample_date=sample_date
        ))


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

        queryset = self.filter_queryset(self.get_queryset())
        return csv_report.get_csv_response(
            queryset,
            self.serializer_class_csv,
            file_name_prefix=file_name_prefix,
            include_additional_fields=include_additional_fields,
            show_display_fields=show_display_fields,
        )


class BaseProjectMethodView(AggregatedViewMixin, BaseProjectApiViewSet):
    permission_classes = [Or(ProjectDataReadOnlyPermission, ProjectPublicPermission)]

    @action(detail=False, methods=["get"])
    def csv(self, request, *args, **kwargs):
        try:
            project = Project.objects.get(pk=kwargs["project_pk"])
        except ObjectDoesNotExist:
            return HttpResponseBadRequest("Project doesn't exist")

        project_name = get_valid_filename(project.name)[:100]
        file_name_prefix = f"{project_name}-{self.drf_label}"

        self.limit_to_project(request, *args, **kwargs)
        kwargs["file_name_prefix"] = file_name_prefix
        return super().csv(request, *args, **kwargs)

    def get_queryset(self):
        project_id = self.kwargs.get("project_pk")
        return self.model.objects.all().sql_table(
            project_id=project_id
        )
