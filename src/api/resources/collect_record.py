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

from ..ingest.utils import ingest_benthicpit, ingest_fishbelt
from ..models import CollectRecord
from ..permissions import ProjectDataPermission
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
)
from ..submission.validations import ERROR, OK, WARN
from ..submission.writer import (
    BenthicLITProtocolWriter,
    BenthicPITProtocolWriter,
    BleachingQuadratCollectionProtocolWriter,
    FishbeltProtocolWriter,
    HabitatComplexityProtocolWriter,
)
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
    queryset = CollectRecord.objects.all().order_by("-updated_by")
    filter_class = CollectRecordFilterSet

    def _validate(self, record_id, request):
        try:
            record = self.queryset.get(id=record_id)
        except CollectRecord.DoesNotExist:
            raise NotFound()

        protocol = record.data.get("protocol")
        if protocol not in PROTOCOLS:
            raise ParseError(ugettext_lazy("{} not supported".format(protocol)))

        if protocol == BENTHICLIT_PROTOCOL:
            validator = BenthicLITProtocolValidation(record, request)
        elif protocol == BENTHICPIT_PROTOCOL:
            validator = BenthicPITProtocolValidation(record, request)
        elif protocol == FISHBELT_PROTOCOL:
            validator = FishBeltProtocolValidation(record, request)
        elif protocol == HABITATCOMPLEXITY_PROTOCOL:
            validator = HabitatComplexityProtocolValidation(record, request)
        elif protocol == BLEACHING_QC_PROTOCOL:
            validator = BleachingQuadratCollectionProtocolValidation(record, request)

        result = validator.validate()
        validations = validator.validations

        return result, validations

    @action(
        detail=False,
        methods=["post"],
        permission_classes=BaseProjectApiViewSet.permission_classes
        + [CollectRecordOwner],
    )
    def validate(self, request, project_pk):
        output = dict()
        record_ids = request.data.get("ids") or []

        for record_id in record_ids:
            result, validation_output = self._validate(record_id, request)
            stage = CollectRecord.SAVED_STAGE
            if result == OK:
                stage = CollectRecord.VALIDATED_STAGE

            validation_timestamp = timezone.now()
            validations = dict(
                status=result,
                results=validation_output,
                last_validated=str(validation_timestamp),
            )

            record = None
            collect_record = None
            try:
                qry = self.queryset.filter(id=record_id)
                profile = None
                if hasattr(request, "user") and hasattr(request.user, "profile"):
                    profile = request.user.profile

                # Using update so updated_on and validation_timestamp matches
                qry.update(
                    stage=stage,
                    validations=validations,
                    updated_on=validation_timestamp,
                    updated_by=profile,
                )
                if qry.count() > 0:
                    collect_record = qry[0]
            except CollectRecord.DoesNotExist:
                pass

            if collect_record:
                record = self.serializer_class(collect_record).data

            output[record_id] = dict(status=result, record=record)

        return Response(output)

    @action(
        detail=False,
        methods=["post"],
        permission_classes=BaseProjectApiViewSet.permission_classes
        + [CollectRecordOwner],
    )
    def submit(self, request, project_pk):
        output = {}
        record_ids = request.data.get("ids")
        for record_id in record_ids:
            collect_record = CollectRecord.objects.get_or_none(id=record_id)
            if collect_record is None:
                output[record_id] = dict(
                    status=ERROR, message=ugettext_lazy("Not found")
                )
                continue

            result, _ = self._validate(record_id, request)
            if result != OK:
                output[record_id] = dict(
                    status=result, message=ugettext_lazy("Invalid collect record")
                )
                continue

            # If validate comes out all good (status == OK) then
            # try parsing and saving the collect record into its
            # components.
            status, result = utils.write_collect_record(collect_record, request)
            if status == utils.VALIDATION_ERROR_STATUS:
                output[record_id] = dict(status=ERROR, message=result)
                continue
            elif status == utils.ERROR_STATUS:
                logger.error(
                    json.dumps(dict(id=record_id, data=collect_record.data)), result
                )
                output[record_id] = dict(
                    status=ERROR, message=ugettext_lazy("System failure")
                )
                continue
            output[record_id] = dict(status=OK, message=ugettext_lazy("Success"))

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

    @action(detail=False, methods=["POST"], permission_classes=[ProjectDataPermission])
    def ingest(self, request, project_pk, *args, **kwargs):

        # TODO: PERMISSIONS
        # TODO: dryrun query parameter
        
        protocol = request.data.get("protocol")
        uploaded_file = request.FILES.get("file")
        profile = request.user.profile
        # print("uploaded_file: {}".format(type(uploaded_file)))
        # print("protocol: {}".format(protocol))
        # print("project_pk: {}".format(project_pk))
        # print(request.user.profile)

        decoded_file = uploaded_file.read().decode("utf-8").splitlines()
        records, errors = ingest_fishbelt(
            decoded_file, project_pk, profile.id, protocol, False
        )

        if errors:
            return Response(errors, status=400)
        return Response(CollectRecordSerializer(records, many=True).data)
