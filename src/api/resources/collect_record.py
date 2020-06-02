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

from ..ingest.utils import ingest
from ..models import CollectRecord
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
    BENTHICLIT_PROTOCOL,
    BENTHICPIT_PROTOCOL,
    BLEACHING_QC_PROTOCOL,
    FISHBELT_PROTOCOL,
    HABITATCOMPLEXITY_PROTOCOL,
    PROTOCOLS,
    submit_collect_records,
    validate_collect_records,
)
from ..submission.validations import ERROR, OK, WARN
from ..utils import truthy
from .base import BaseAPIFilterSet, BaseAPISerializer, BaseProjectApiViewSet

logger = logging.getLogger(__name__)


class CollectRecordOwner(permissions.BasePermission):
    def has_permission(self, request, view):
        record_ids = request.data.get("ids") or []
        if not record_ids:
            return True

        profile = getattr(request.user, "profile")
        count = CollectRecord.objects.filter(id__in=record_ids, profile=profile).count()
        return count == len(record_ids)


class CollectRecordSerializer(BaseAPISerializer):
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

    def filter_queryset(self, queryset):
        user = self.request.user
        show_all = "showall" in self.request.query_params

        if show_all is True:
            return queryset

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
        record_ids = request.data.get("ids") or []
        profile = request.user.profile
        try:
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
        record_ids = request.data.get("ids")
        profile = request.user.profile
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

        if protocol is None:
            return Response("Protocol not supported", status=400)

        content_type = uploaded_file.content_type
        if content_type not in supported_content_types:
            return Response("File type not supported", status=400)

        decoded_file = uploaded_file.read().decode("utf-8-sig").splitlines()
        records, ingest_output = ingest(
            protocol,
            decoded_file,
            project_pk,
            profile.id,
            None,
            dry_run=dryrun,
            clear_existing=clearexisting,
            bulk_validation=True,
            bulk_submission=False,
            validation_suppressants=validate_config,
            serializer_class=CollectRecordSerializer,
        )

        if "errors" in ingest_output:
            errors = ingest_output["errors"]
            return Response(errors, status=400)

        records = ingest_output.get("validate")
        return Response(records)
