import json
import logging
import uuid

from django.db import connection, transaction
from django.utils import timezone
from django.utils.translation import ugettext_lazy
from rest_framework import permissions, status as drf_status
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, ParseError, ValidationError
from rest_framework.response import Response

from .mixins import CreateOrUpdateSerializerMixin
from ..ingest.utils import InvalidSchema, ingest
from ..models import (
    BENTHICLIT_PROTOCOL,
    BENTHICPIT_PROTOCOL,
    FISHBELT_PROTOCOL,
    HABITATCOMPLEXITY_PROTOCOL,
    BLEACHINGQC_PROTOCOL,
    BENTHIC_PHOTO_QUADRAT_TRANSECT,
    PROTOCOL_MAP,
    CollectRecord,
)
from ..permissions import ProjectDataAdminPermission, ProjectDataPermission
from ..submission import utils
from ..submission.protocol_validations import (
    BenthicLITProtocolValidation,
    BenthicPITProtocolValidation,
    BleachingQuadratCollectionProtocolValidation,
    FishBeltProtocolValidation,
    HabitatComplexityProtocolValidation,
)
from ..submission.utils import (
    submit_collect_records,
    submit_collect_records_v2,
    validate_collect_records,
    validate_collect_records_v2,
)
from ..submission.validations import ERROR, OK, WARN
from ..utils import truthy
from .base import BaseAPIFilterSet, BaseAPISerializer, BaseProjectApiViewSet

logger = logging.getLogger(__name__)


class CollectRecordOwner(permissions.BasePermission):
    def has_permission(self, request, view):
        record_ids = request.data.get("ids") or []
        pk = view.kwargs.get("pk")
        if pk:
            record_ids = [pk]
        elif not record_ids:
            return True

        profile = getattr(request.user, "profile")
        count = CollectRecord.objects.filter(id__in=record_ids, profile=profile).count()
        return count == len(record_ids)


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
    filter_class = CollectRecordFilterSet
    permission_classes = BaseProjectApiViewSet.permission_classes + [CollectRecordOwner]

    def filter_queryset(self, queryset):
        user = self.request.user
        profile = user.profile

        return queryset.filter(profile=profile)

    @action(
        detail=False,
        methods=["post"],
        permission_classes=BaseProjectApiViewSet.permission_classes
        + [CollectRecordOwner],
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
            raise ParseError(err.message)

        return Response(output)

    @action(
        detail=False,
        methods=["post"],
        permission_classes=BaseProjectApiViewSet.permission_classes
        + [CollectRecordOwner],
    )
    def submit(self, request, project_pk):
        validation_version = request.data.get("version") or "1"
        record_ids = request.data.get("ids")
        profile = request.user.profile

        if validation_version == "2":
            output = submit_collect_records_v2(
                profile,
                record_ids,
                CollectRecordSerializer
            )
        else:
            output = submit_collect_records(
                profile, record_ids
            )

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
            return Response(f"Missing required fields: {', '.join(missing_required_fields)}", status=400)

        if "errors" in ingest_output:
            errors = ingest_output["errors"]
            return Response(errors, status=400)

        return Response(CollectRecordSerializer(records, many=True).data)
