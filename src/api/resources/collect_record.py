import csv
import json
import logging
import uuid

from django.db import connection
from rest_condition import And
from rest_framework import status as drf_status
from rest_framework.decorators import action
from rest_framework.exceptions import ParseError
from rest_framework.permissions import SAFE_METHODS
from rest_framework.response import Response

from ..ingest.utils import (
    InvalidSchema,
    get_ingest_project_choices,
    get_su_serializer,
    ingest,
)
from ..models import PROTOCOL_MAP, CollectRecord
from ..permissions import (
    CollectRecordOwner,
    ProjectDataAdminPermission,
    ProjectDataPermission,
)
from ..submission.utils import submit_collect_records, validate_collect_records
from ..utils import truthy
from .base import BaseAPIFilterSet, BaseAPISerializer, BaseProjectApiViewSet
from .mixins import CreateOrUpdateSerializerMixin

logger = logging.getLogger(__name__)
cr_permissions = [And(ProjectDataPermission, CollectRecordOwner)]


def get_unicode_error(uploaded_file, byte_position, chunk_size=8192):
    error_message = "Character encoding error; CSV file should be encoded as UTF-8."

    if not isinstance(byte_position, int) or byte_position < 0:
        return f"{error_message} Problematic character at position {byte_position}."

    uploaded_file.seek(0)
    cumulative_byte_count = 0

    while True:
        chunk = uploaded_file.read(chunk_size)
        if not chunk:
            break  # End of file

        chunk_start_byte = cumulative_byte_count
        chunk_end_byte = cumulative_byte_count + len(chunk)

        if chunk_start_byte <= byte_position < chunk_end_byte:
            # Extract the relevant portion of the chunk up to the problematic byte
            relevant_chunk = chunk[: byte_position - chunk_start_byte + 1]
            partially_decoded = relevant_chunk.decode("utf-8-sig", errors="replace")

            lines = partially_decoded.splitlines()
            problematic_cell_content = None
            problematic_row_index = 0
            problematic_column_index = 0

            for row_index, line in enumerate(lines):
                encoded_line = line.encode("utf-8")  # Re-encode to match byte positions
                line_start_byte = cumulative_byte_count
                line_end_byte = line_start_byte + len(encoded_line)

                if line_start_byte <= byte_position < line_end_byte:
                    # The problematic byte is in this line
                    reader = csv.reader([line])  # Parse the line as CSV
                    row = next(reader)

                    # Locate the specific cell
                    cell_start_byte = line_start_byte
                    for column_index, cell in enumerate(row):
                        encoded_cell = cell.encode("utf-8")
                        cell_end_byte = cell_start_byte + len(encoded_cell)

                        if cell_start_byte <= byte_position < cell_end_byte:
                            problematic_cell_content = cell
                            problematic_column_index = column_index
                            break

                        cell_start_byte = cell_end_byte + 1  # Account for the comma separator
                    break

                cumulative_byte_count += len(encoded_line) + 1  # Include newline byte

            # Construct the error message
            if problematic_cell_content is not None:
                error_message = (
                    f"{error_message} Problematic character occurs in row {problematic_row_index + 1}, "
                    f"column {problematic_column_index + 1}: {problematic_cell_content}"
                )
            else:
                error_message = (
                    f"{error_message} Unable to locate the problematic character in the chunk."
                )

            return error_message

        # Move cumulative count to the next chunk
        cumulative_byte_count = chunk_end_byte

    # If we reach here, the problematic byte was not found
    return f"{error_message} Problematic byte position {byte_position} not found in the file."


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
        record_ids = request.data.get("ids") or []
        profile = request.user.profile
        try:
            output = validate_collect_records(profile, record_ids, CollectRecordSerializer)
        except ValueError as err:
            raise ParseError(err) from err

        return Response(output)

    @action(
        detail=False,
        methods=["post"],
        permission_classes=cr_permissions,
    )
    def submit(self, request, project_pk):
        record_ids = request.data.get("ids")
        profile = request.user.profile

        output = submit_collect_records(profile, record_ids, CollectRecordSerializer)

        return Response(output)

    @action(detail=False, methods=["POST"], permission_classes=[ProjectDataPermission])
    def missing(self, request, *args, **kwargs):
        ids = request.data.get("id")

        if ids is None or isinstance(ids, list) is False:
            return Response("Invalid 'id' value.", status=drf_status.HTTP_400_BAD_REQUEST)

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

        query_sql = "SELECT * FROM unnest(%s) _pk_ EXCEPT ALL SELECT _pk_ FROM (" + sql + ") as foo"
        query_params = [uuids]
        query_params.extend(list(params))
        with connection.cursor() as cursor:
            cursor.execute(query_sql, params=query_params)
            missing_ids = [row[0] for row in cursor.fetchall()]

        return Response(dict(missing_ids=missing_ids))

    @action(detail=False, methods=["POST"], permission_classes=[ProjectDataAdminPermission])
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
        validate = truthy(request.data.get("validate"))

        validate_config = None
        try:
            config = request.data.get("validate_config")
            if config:
                validate_config = json.loads(config)
        except (ValueError, TypeError):
            return Response("Invalid validate_config", status=drf_status.HTTP_400_BAD_REQUEST)

        if protocol is None:
            return Response("Missing protocol", status=drf_status.HTTP_400_BAD_REQUEST)

        if uploaded_file is None:
            return Response("Missing file", status=drf_status.HTTP_400_BAD_REQUEST)

        if protocol not in PROTOCOL_MAP:
            return Response("Protocol not supported", status=drf_status.HTTP_400_BAD_REQUEST)

        content_type = uploaded_file.content_type
        if content_type not in supported_content_types:
            return Response("File type not supported", status=drf_status.HTTP_400_BAD_REQUEST)

        try:
            decoded_file = uploaded_file.read().decode("utf-8-sig").splitlines()
        except UnicodeDecodeError as e:
            error_message = get_unicode_error(uploaded_file, e.start)
            return Response(error_message, status=drf_status.HTTP_400_BAD_REQUEST)

        try:
            records, ingest_output = ingest(
                protocol,
                decoded_file,
                project_pk,
                profile.id,
                None,
                dry_run=dryrun,
                clear_existing=clearexisting,
                bulk_validation=validate,
                bulk_submission=False,
                validation_suppressants=validate_config,
                serializer_class=CollectRecordSerializer,
            )
        except InvalidSchema as schema_error:
            missing_required_fields = schema_error.errors
            return Response(
                f"Missing required fields: {', '.join(missing_required_fields)}",
                status=drf_status.HTTP_400_BAD_REQUEST,
            )

        if "errors" in ingest_output:
            return Response(ingest_output["errors"], status=drf_status.HTTP_400_BAD_REQUEST)
        elif "validate" in ingest_output:
            return Response(ingest_output["validate"], status=drf_status.HTTP_400_BAD_REQUEST)

        return Response(CollectRecordSerializer(records, many=True).data)

    @action(
        detail=False,
        methods=SAFE_METHODS,
        permission_classes=[ProjectDataAdminPermission],
        url_path=r"ingest_schema/(?P<sample_unit>\w+)",
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
                    choices = [name for name, choice_id in choice_sets[field.field_name].items()]

                field_def = {
                    "name": fieldname_simple,
                    "label": label,
                    "required": field.required,
                    "help_text": field.help_text,
                    "choices": choices,
                }
                schema.append(field_def)

        return Response(schema, status=200)
