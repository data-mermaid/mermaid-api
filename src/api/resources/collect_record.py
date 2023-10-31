import json
import logging
import uuid

from django.db import connection
from rest_condition import And, Or
from rest_framework import status as drf_status
from rest_framework.decorators import action
from rest_framework.exceptions import ParseError
from rest_framework.permissions import SAFE_METHODS
from rest_framework.response import Response

from .mixins import CreateOrUpdateSerializerMixin
from ..ingest.utils import (
    InvalidSchema,
    ingest,
    get_ingest_project_choices,
    get_su_serializer,
)
from ..models import (
    PROTOCOL_MAP,
    CollectRecord,
)
from ..permissions import (
    CollectRecordOwner,
    ProjectDataAdminPermission,
    ProjectDataPermission,
)
from ..submission.utils import (
    submit_collect_records,
    submit_collect_records_v2,
    validate_collect_records,
    validate_collect_records_v2,
)
from ..utils import truthy
from .base import BaseAPIFilterSet, BaseAPISerializer, BaseProjectApiViewSet


logger = logging.getLogger(__name__)
cr_permissions = [And(BaseProjectApiViewSet.permission_classes[0], CollectRecordOwner)]


class CollectRecordSerializer(CreateOrUpdateSerializerMixin, BaseAPISerializer):
    class Meta:
        model = CollectRecord
        exclude = []


class CollectRecordFilterSet(BaseAPIFilterSet):
    class Meta:
        model = CollectRecord
        fields = ["stage"]


class CollectRecordViewSet(BaseProjectApiViewSet):
    serializer_class = CollectRecordSerializer
    queryset = CollectRecord.objects.all().order_by("id")
    filterset_class = CollectRecordFilterSet
    permission_classes = cr_permissions

    def filter_queryset(self, queryset):
        user = self.request.user
        profile = user.profile

        return queryset.filter(profile=profile)

    @action(
        detail=False,
        methods=["post"],
        permission_classes=cr_permissions,
    )
    def validate(self, request, project_pk):
        output = dict()
        validation_version = request.data.get("version") or "1"
        record_ids = request.data.get("ids") or []
        profile = request.user.profile
        try:
            if validation_version == "2":
                output = validate_collect_records_v2(
                    profile, record_ids, CollectRecordSerializer
                )
            else:
                output = validate_collect_records(
                    profile, record_ids, CollectRecordSerializer
                )
        except ValueError as err:
            raise ParseError(err) from err

        return Response(output)

    @action(
        detail=False,
        methods=["post"],
        permission_classes=cr_permissions,
    )
    def submit(self, request, project_pk):
        submit_version = request.data.get("version") or "1"
        record_ids = request.data.get("ids")
        profile = request.user.profile

        if str(submit_version) == "2":
            output = submit_collect_records_v2(
                profile, record_ids, CollectRecordSerializer
            )
        else:
            output = submit_collect_records(profile, record_ids)

        return Response(output)

    @action(detail=False, methods=["POST"], permission_classes=[ProjectDataPermission])
    def missing(self, request, *args, **kwargs):
        ids = request.data.get("id")

        if ids is None or isinstance(ids, list) is False:
            return Response(
                "Invalid 'id' value.", status=drf_status.HTTP_400_BAD_REQUEST
            )

        if len(ids) == 0:
            return Response([])

        try:
            uuids = [uuid.UUID(pk) for pk in ids]
        except (ValueError, TypeError):
            return Response("Invalid uuid", status=drf_status.HTTP_400_BAD_REQUEST)

        qs = self.get_queryset()

        table_name = qs.model._meta.db_table
        pk_name = qs.model._meta.pk.get_attname_column()[1]

        qs = qs.extra(select={"_pk_": '"{}"."{}"'.format(table_name, pk_name)})

        sql, params = qs.query.get_compiler(using=qs.db).as_sql()

        query_sql = (
            "SELECT * FROM unnest(%s) _pk_ "
            "EXCEPT ALL "
            "SELECT _pk_ FROM (" + sql + ") as foo"
        )

        query_params = [uuids]
        query_params.extend(list(params))
        with connection.cursor() as cursor:
            cursor.execute(query_sql, params=query_params)
            missing_ids = [row[0] for row in cursor.fetchall()]

        return Response(dict(missing_ids=missing_ids))

    @action(
        detail=False, methods=["POST"], permission_classes=[ProjectDataAdminPermission]
    )
    def ingest(self, request, project_pk, *args, **kwargs):
        supported_content_types = (
            "application/csv",
            "application/x-csv",
            "text/csv",
            "text/comma-separated-values",
            "text/x-comma-separated-values",
        )

        protocol = request.data.get("protocol")
        uploaded_file = request.FILES.get("file")
        profile = request.user.profile
        dryrun = truthy(request.data.get("dryrun"))
        clearexisting = truthy(request.data.get("clearexisting"))

        validate_config = None
        try:
            config = request.data.get("validate_config")
            if config:
                validate_config = json.loads(config)
        except (ValueError, TypeError):
            return Response("Invalid validate_config", status=400)

        if protocol is None:
            return Response("Missing protocol", status=400)

        if uploaded_file is None:
            return Response("Missing file", status=400)

        if protocol not in PROTOCOL_MAP:
            return Response("Protocol not supported", status=400)

        content_type = uploaded_file.content_type
        if content_type not in supported_content_types:
            return Response("File type not supported", status=400)

        decoded_file = uploaded_file.read().decode("utf-8-sig").splitlines()
        try:
            records, ingest_output = ingest(
                protocol,
                decoded_file,
                project_pk,
                profile.id,
                None,
                dry_run=dryrun,
                clear_existing=clearexisting,
                bulk_validation=False,
                bulk_submission=False,
                validation_suppressants=validate_config,
                serializer_class=CollectRecordSerializer,
            )
        except InvalidSchema as schema_error:
            missing_required_fields = schema_error.errors
            return Response(
                f"Missing required fields: {', '.join(missing_required_fields)}",
                status=400,
            )

        if "errors" in ingest_output:
            errors = ingest_output["errors"]
            return Response(errors, status=400)

        return Response(CollectRecordSerializer(records, many=True).data)

    @action(
        detail=False,
        methods=SAFE_METHODS,
        permission_classes=[ProjectDataAdminPermission],
        url_path="ingest_schema/(?P<sample_unit>\w+)",
        url_name="ingest-schemas-json",
    )
    def ingest_schema_json(self, request, project_pk, sample_unit, *args, **kwargs):
        serializer = get_su_serializer(sample_unit)
        schema = []
        project_choices = None
        if project_pk:
            project_choices = get_ingest_project_choices(project_pk)
        instance = serializer(project_choices=project_choices, many=True)
        choice_sets = instance.get_choices_sets()

        for label in instance.child.get_schema_labels():
            fieldname, field = instance.child.get_schemafield(label)
            if field:
                fieldname_simple = "__".join(fieldname.split("__")[1:])
                choices = None
                if field.field_name in choice_sets and choice_sets[field.field_name]:
                    choices = [
                        name
                        for name, choice_id in choice_sets[field.field_name].items()
                    ]

                field_def = {
                    "name": fieldname_simple,
                    "label": label,
                    "required": field.required,
                    "help_text": field.help_text,
                    "choices": choices,
                }
                schema.append(field_def)

        return Response(schema, status=200)
