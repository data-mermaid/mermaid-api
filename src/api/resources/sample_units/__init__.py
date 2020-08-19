import uuid
from datetime import datetime

from collections import defaultdict
from django.utils.translation import ugettext_lazy as _
from django.utils.text import get_valid_filename
from django.http import StreamingHttpResponse, HttpResponseBadRequest
from ...models import Management, Observer
from ...resources.base import BaseProjectApiViewSet
from ...resources.management import get_rules
from rest_framework.decorators import action
from rest_framework_gis.pagination import GeoJsonPagination
from rest_condition import Or
from ...auth_backends import AnonymousJWTAuthentication
from ...permissions import *
from ...reports import RawCSVReport
from ...report_serializer import *

from ...reports import csv_report


def to_governance(field, row, serializer_instance):
    transect_method = serializer_instance.transect_method or None
    sample_event_path = serializer_instance.sample_event_path or None
    if transect_method is None or sample_event_path is None:
        return ""
    parties = ""
    project_pk = row.get("{}__site__project_id".format(sample_event_path))
    management_id = row.get("{}__management_id".format(sample_event_path))
    lookup = serializer_instance.serializer_cache.get(
        "{}_lookups-management_parties-{}".format(transect_method, project_pk)
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
    transect_method = serializer_instance.transect_method or None
    sample_event_path = serializer_instance.sample_event_path or None
    if transect_method is None or sample_event_path is None:
        return ""
    project_pk = row.get("{}__site__project_id".format(sample_event_path))
    management_id = row.get("{}__management_id".format(sample_event_path))
    lookup = serializer_instance.serializer_cache.get(
        "{}_lookups-management_rules-{}".format(transect_method, project_pk)
    )
    if lookup:
        return lookup.get(str(management_id))

    return get_rules(Management.objects.get_or_none(id=management_id))


def to_observers(field, row, serializer_instance):
    transect_method = serializer_instance.transect_method or None
    sample_event_path = serializer_instance.sample_event_path or None
    tid = row.get("{}_id".format(transect_method))
    if tid is None or transect_method is None or sample_event_path is None:
        return ""

    project_pk = row.get("{}__site__project_id".format(sample_event_path))
    lookup = serializer_instance.serializer_cache.get(
        "{}_lookups-observers-{}".format(transect_method, project_pk)
    )
    if lookup:
        observers = lookup.get(str(tid))
    else:
        transect = serializer_instance.Meta.model.objects.get_or_none(id=tid)
        if transect is None:
            return ""

        observers = sorted(
            [o.profile_name for o in transect.observers.all().iterator()]
        )
    return ",".join(observers)


# class SampleEventReportSerializerMeta(type):
#     def __new__(mcs, clsname, bases, dct):
#         sample_event_path = dct.get("sample_event_path")
#         dct["fields"] = [
#             ReportField(
#                 "{}__site__project__name".format(sample_event_path), "Project name"
#             ),
#             ReportField("{}__site__country__name".format(sample_event_path), "Country"),
#             ReportField("{}__site__name".format(sample_event_path), "Site"),
#             ReportField(
#                 "{}__site__location".format(sample_event_path), "Latitude", to_latitude
#             ),
#             ReportField(
#                 "{}__site__location".format(sample_event_path),
#                 "Longitude",
#                 to_longitude,
#             ),
#             ReportField(
#                 "{}__site__exposure__name".format(sample_event_path), "Exposure"
#             ),
#             ReportField(
#                 "{}__site__reef_type__name".format(sample_event_path), "Reef type"
#             ),
#             ReportField(
#                 "{}__site__reef_zone__name".format(sample_event_path), "Reef zone"
#             ),
#             ReportField("{}__sample_date".format(sample_event_path), "Year", to_year),
#             ReportField("{}__sample_date".format(sample_event_path), "Month", to_month),
#             ReportField("{}__sample_date".format(sample_event_path), "Day", to_day),
#             ReportField(
#                 "{}__sample_time".format(sample_event_path), "Start time", to_unicode
#             ),
#             ReportField("{}__tide__name".format(sample_event_path), "Tide"),
#             ReportField("{}__visibility__name".format(sample_event_path), "Visibility"),
#             ReportField("{}__current__name".format(sample_event_path), "Current"),
#             ReportField("{}__depth".format(sample_event_path), "Depth", to_float),
#             ReportField(
#                 "{}__management__name".format(sample_event_path), "Management name"
#             ),
#             ReportField(
#                 "{}__management__name_secondary".format(sample_event_path),
#                 "Management secondary name",
#             ),
#             ReportField(
#                 "{}__management__est_year".format(sample_event_path),
#                 "Management year established",
#             ),
#             ReportField(
#                 "{}__management__size".format(sample_event_path),
#                 "Management size",
#                 to_float,
#             ),
#             ReportMethodField("Governance", to_governance),
#             ReportField(
#                 "{}__management__compliance__name".format(sample_event_path),
#                 "Estimated compliance",
#             ),
#             ReportMethodField("Management rules", to_management_rules),
#             ReportMethodField("Observer", to_observers),
#             ReportField("{}__site__notes".format(sample_event_path), "Site notes"),
#             ReportField("{}__notes".format(sample_event_path), "Sampling event notes"),
#             ReportField(
#                 "{}__management__notes".format(sample_event_path), "Management notes"
#             ),
#         ]

#         obs_fields = dct.get("obs_fields")
#         if obs_fields:
#             for f in obs_fields:
#                 dct["fields"].insert(f[0], f[1])

#         return super(SampleEventReportSerializerMeta, mcs).__new__(
#             mcs, clsname, bases, dct
#         )


# class SampleEventReportSerializer(ReportSerializer):
#     serializer_cache = dict()
#     transect_method = None
#     sample_event_path = None

#     def preserialize(self, queryset=None):
#         self.serializer_cache = dict()
#         try:
#             values = (
#                 queryset.values_list(
#                     "{}__site__project_id".format(self.sample_event_path), flat=True
#                 )
#                 or []
#             )
#             if not values:
#                 raise ObjectDoesNotExist
#             project_pk = values[0]
#         except ObjectDoesNotExist:
#             return

#         # Observers
#         kwargs = {
#             "transectmethod__{}__site__project_id".format(
#                 self.sample_event_path
#             ): project_pk
#         }
#         observers = (
#             Observer.objects.select_related("transectmethod")
#             .filter(**kwargs)
#             .iterator()
#         )
#         observer_lookup = defaultdict(list)
#         for o in observers:
#             observer_lookup[str(o.transectmethod.id)].append(o.profile.full_name)
#         for transect_method_id, observers in observer_lookup.items():
#             observer_lookup[transect_method_id] = sorted(observers)
#         if len(observer_lookup.keys()) > 0:
#             self.serializer_cache[
#                 "{}_lookups-observers-{}".format(self.transect_method, project_pk)
#             ] = observer_lookup

#         # Management Parties and Rules
#         management_parties_lookup = dict()
#         management_rules_lookup = dict()
#         for m in Management.objects.filter(project_id=project_pk):
#             parties = m.parties.all().order_by("name").values_list("name", flat=True)
#             management_parties_lookup[str(m.id)] = ",".join(parties)
#             management_rules_lookup[str(m.id)] = get_rules(m)

#         if len(management_parties_lookup.keys()) > 0:
#             self.serializer_cache[
#                 "{}_lookups-management_parties-{}".format(
#                     self.transect_method, project_pk
#                 )
#             ] = management_parties_lookup
#             self.serializer_cache[
#                 "{}_lookups-management_rules-{}".format(
#                     self.transect_method, project_pk
#                 )
#             ] = management_rules_lookup


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


class BaseGeoJsonPagination(GeoJsonPagination):
    page_size = 100
    page_size_query_param = "limit"
    max_page_size = 1000


class BaseProjectMethodView(BaseProjectApiViewSet):
    drf_label = ""
    project_policy = None
    serializer_class_geojson = None
    serializer_class_csv = None
    method_authentication_classes = {"GET": [AnonymousJWTAuthentication]}
    permission_classes = [Or(ProjectDataReadOnlyPermission, ProjectPublicPermission)]
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
        is_report_field = truthy(request.query_params.get("field_report"))
        show_display_fields = is_report_field
        include_additional_fields = not is_report_field

        try:
            project = Project.objects.get(pk=kwargs["project_pk"])
        except ObjectDoesNotExist:
            return HttpResponseBadRequest("Project doesn't exist")

        project_name = get_valid_filename(project.name)[:100]
        file_name_prefix = f"{project_name}-{self.drf_label}"

        self.limit_to_project(request, *args, **kwargs)
        queryset = self.filter_queryset(self.get_queryset())
        return csv_report.get_csv_response(
            queryset,
            self.serializer_class_csv,
            file_name_prefix=file_name_prefix,
            include_additional_fields=include_additional_fields,
            show_display_fields=show_display_fields,
        )



        # try:
        #     project = Project.objects.get(pk=kwargs["project_pk"])
        # except ObjectDoesNotExist:
        #     return HttpResponseBadRequest("Project doesn't exist")
        # self.limit_to_project(request, *args, **kwargs)
        # self.serializer_class = self.serializer_class_csv

        # self.queryset = self.filter_queryset(self.get_queryset())
        # serializer = self.get_serializer(self.get_queryset(), many=True)
        # fields = self._get_fields(serializer)
        # serialized_data = self.csv_data(fields, serializer)
        # report = RawCSVReport()
        # stream = report.stream(list(fields), serialized_data)

        # response = StreamingHttpResponse(stream, content_type="text/csv")
        # ts = datetime.utcnow().strftime("%Y%m%d")
        # projname = get_valid_filename(project.name)[:100]
        # response["Content-Disposition"] = 'attachment; filename="{}-{}-{}.csv"'.format(
        #     self.drf_label, projname, ts
        # )
        # return response
