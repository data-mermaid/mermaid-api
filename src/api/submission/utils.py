import dataclasses
import json
import logging
import time

from django.core.exceptions import ValidationError as DJValidationError
from django.db import transaction
from django.db.utils import OperationalError
from django.utils import timezone
from django.utils.translation import gettext_lazy
from opentelemetry import trace as otel_trace
from rest_framework.exceptions import ValidationError

from ..exceptions import check_uuid
from ..mocks import MockRequest
from ..models import (
    BENTHICLIT_PROTOCOL,
    BENTHICPIT_PROTOCOL,
    BENTHICPQT_PROTOCOL,
    BLEACHINGQC_PROTOCOL,
    FISHBELT_PROTOCOL,
    HABITATCOMPLEXITY_PROTOCOL,
    MACROINVERTEBRATE_PROTOCOL,
    PROTOCOL_MAP,
    AuditRecord,
    CollectRecord,
    Image,
)
from ..signals import post_submit
from ..utils.related import defer_project_updated_on
from ..utils.sample_unit_methods import create_audit_record
from ..utils.summary_cache import add_project_to_queue
from .validations import (
    ValidationRunner,
    belt_fish,
    belt_invert,
    benthic_lit,
    benthic_photo_quadrat_transect,
    benthic_pit,
    bleaching_quadrat_collection,
    habitat_complexity,
)
from .validations.statuses import ERROR, IGNORE, OK, WARN
from .validations.validators import DrySubmitValidator
from .writer import (
    BeltInvertProtocolWriter,
    BenthicLITProtocolWriter,
    BenthicPhotoQuadratTransectProtocolWriter,
    BenthicPITProtocolWriter,
    BleachingQuadratCollectionProtocolWriter,
    FishbeltProtocolWriter,
    HabitatComplexityProtocolWriter,
)

SUCCESS_STATUS = 200
VALIDATION_ERROR_STATUS = 400
ERROR_STATUS = 500

# See write_collect_record() for why deadlocks get retried.
DEADLOCK_MAX_RETRIES = 3
DEADLOCK_RETRY_DELAY = 0.25  # seconds; multiplied by attempt number

logger = logging.getLogger(__name__)


def _is_deadlock_error(err):
    return isinstance(err, OperationalError) and "deadlock detected" in str(err).lower()


def get_writer(collect_record, context):
    protocol = collect_record.data.get("protocol")
    if protocol not in PROTOCOL_MAP:
        return None

    if protocol == BENTHICLIT_PROTOCOL:
        return BenthicLITProtocolWriter(collect_record, context)

    elif protocol == BENTHICPIT_PROTOCOL:
        return BenthicPITProtocolWriter(collect_record, context)

    elif protocol == BENTHICPQT_PROTOCOL:
        return BenthicPhotoQuadratTransectProtocolWriter(collect_record, context)

    elif protocol == FISHBELT_PROTOCOL:
        return FishbeltProtocolWriter(collect_record, context)

    elif protocol == HABITATCOMPLEXITY_PROTOCOL:
        return HabitatComplexityProtocolWriter(collect_record, context)

    elif protocol == BLEACHINGQC_PROTOCOL:
        return BleachingQuadratCollectionProtocolWriter(collect_record, context)

    elif protocol == MACROINVERTEBRATE_PROTOCOL:
        return BeltInvertProtocolWriter(collect_record, context)


def format_serializer_errors(validationerror):
    output = dict()
    if hasattr(validationerror, "get_full_details"):
        details = validationerror.get_full_details()
        for identifier, record in details.items():
            output[identifier] = [str(r.get("message")) for r in record]
    else:
        output["exception"] = validationerror.messages
    return output


tracer = otel_trace.get_tracer("api.submission")


class RecordTraceAttributes:
    """
    Adds the protocol and size of each validated or submitted collect record to
    its span and, summed over the records, to the request span. They are sent
    as X-Ray annotations, so traces can be filtered and compared by size.
    """

    def __init__(self):
        self.request_span = otel_trace.get_current_span()
        self.protocols = set()
        self.totals = {"mermaid_record_count": 0, "mermaid_obs_count": 0, "mermaid_image_count": 0}

    def _set_annotations(self, span, attributes):
        span.set_attributes({**attributes, "aws.xray.annotations": list(attributes)})

    def add(self, span, record):
        data = record.data or {}
        protocol = data.get("protocol") or ""
        image_count = 0
        if data.get("image_classification") and span.is_recording():
            image_count = Image.objects.filter(collect_record_id=record.id).count()
        attributes = {
            "mermaid_protocol": protocol,
            "mermaid_obs_count": sum(
                len(v) for k, v in data.items() if k.startswith("obs_") and isinstance(v, list)
            ),
            "mermaid_image_count": image_count,
        }
        self._set_annotations(span, attributes)

        self.protocols.add(protocol)
        self.totals["mermaid_record_count"] += 1
        self.totals["mermaid_obs_count"] += attributes["mermaid_obs_count"]
        self.totals["mermaid_image_count"] += image_count
        self._set_annotations(
            self.request_span,
            {**self.totals, "mermaid_protocol": ",".join(sorted(self.protocols))},
        )


def format_exception_errors(err):
    identifier = f"{str(type(err).__name__)}"
    msg = ""
    if hasattr(err, "message"):
        msg = err.message
    elif err.args:
        msg = ["; ".join(str(arg) for arg in err.args)]
    return {identifier: [msg]}


def _write_collect_record_once(collect_record, request, dry_run=False):
    status = None
    result = None
    context = {"request": request}
    writer = get_writer(collect_record, context)
    with (
        tracer.start_as_current_span("write_collect_record", attributes={"dry_run": dry_run}),
        transaction.atomic(),
    ):
        sid = transaction.savepoint()
        try:
            # One project save per write in place of one per saved record. It
            # also keeps the project row lock short.
            with defer_project_updated_on():
                writer.write()
            status = SUCCESS_STATUS
        except (ValidationError, DJValidationError) as ve:
            result = format_serializer_errors(ve)
            status = VALIDATION_ERROR_STATUS
        except Exception as err:
            logger.exception("write_collect_record: {}".format(getattr(collect_record, "id")))
            status = ERROR_STATUS
            # A deadlock here can't be resolved by swallowing it into a normal
            # ERROR_STATUS result - the transaction needs to be retried from
            # scratch. Let it propagate to write_collect_record's retry loop.
            if _is_deadlock_error(err):
                raise
            result = format_exception_errors(err)
        finally:
            if dry_run is True or status != SUCCESS_STATUS:
                transaction.savepoint_rollback(sid)
            else:
                create_audit_record(
                    request.user.profile, AuditRecord.SUBMIT_RECORD_EVENT_TYPE, collect_record
                )
                collect_record_id = collect_record.id
                collect_record.delete()
                transaction.savepoint_commit(sid)

                collect_record.id = collect_record_id
                post_submit.send(
                    sender=collect_record.__class__,
                    instance=collect_record,
                )

                add_project_to_queue(collect_record.project_id)
        return status, result


def write_collect_record(collect_record, request, dry_run=False):
    """
    Concurrent submissions to the same project can deadlock while writing
    revision records (see api/models/revisions.py) - either while writer.write()
    saves observations/sample units, or while the collect record itself is
    deleted on submit. Postgres aborts the transaction when it detects a
    deadlock, so it can't be recovered from inside that transaction; it has
    to be retried from scratch with a fresh one, which is what this wraps
    _write_collect_record_once() in a loop to do.
    """
    for attempt in range(DEADLOCK_MAX_RETRIES + 1):
        try:
            return _write_collect_record_once(collect_record, request, dry_run=dry_run)
        except OperationalError as err:
            if not _is_deadlock_error(err):
                raise

            if attempt == DEADLOCK_MAX_RETRIES:
                logger.exception(
                    "write_collect_record: deadlock retries exhausted for {}".format(
                        getattr(collect_record, "id")
                    )
                )
                return ERROR_STATUS, format_exception_errors(err)

            logger.warning(
                "write_collect_record: deadlock detected for %s, retrying (attempt %s/%s)",
                getattr(collect_record, "id"),
                attempt + 1,
                DEADLOCK_MAX_RETRIES,
            )
            time.sleep(DEADLOCK_RETRY_DELAY * (attempt + 1))
            refetched = CollectRecord.objects.get_or_none(id=collect_record.id)
            if refetched is None:
                return ERROR_STATUS, gettext_lazy("Not found")
            collect_record = refetched


def validate(validator_cls, model_cls, qry_params=None):
    validator_identifier = "_root_"
    qry_params = qry_params or dict()
    records = model_cls.objects.filter(**qry_params)

    validation_timestamp = timezone.now()
    for record in records.iterator():
        validator = validator_cls(pk=None)
        validator.identifier = validator_identifier
        validator.instance = record
        result = validator.validate()

        existing_validations = record.validations or dict()
        existing_status = existing_validations.get("status")
        existing_logs = existing_validations.get("results")
        has_updates = existing_status != result or existing_logs != validator.logs
        if has_updates is False:
            continue

        validations = dict(
            status=result,
            results=validator.logs,
            last_validated=str(validation_timestamp),
        )
        record.validations = validations
        model_cls.objects.filter(id=record.id).update(
            validations=validations, updated_on=validation_timestamp
        )


PROTOCOL_VALIDATIONS = {
    BENTHICLIT_PROTOCOL: benthic_lit.benthic_lit_validations,
    BENTHICPIT_PROTOCOL: benthic_pit.benthic_pit_validations,
    FISHBELT_PROTOCOL: belt_fish.belt_fish_validations,
    HABITATCOMPLEXITY_PROTOCOL: habitat_complexity.habcomp_validations,
    BLEACHINGQC_PROTOCOL: bleaching_quadrat_collection.bleaching_quadrat_collection_validations,
    MACROINVERTEBRATE_PROTOCOL: belt_invert.belt_invert_validations,
}


def _get_protocol_validations(record):
    protocol = record.data.get("protocol")
    if protocol not in PROTOCOL_MAP:
        raise ValueError(gettext_lazy(f"{protocol} not supported"))

    if protocol == BENTHICPQT_PROTOCOL:
        if record.data.get("image_classification"):
            return benthic_photo_quadrat_transect.bpqt_classification_validations
        return benthic_photo_quadrat_transect.bpqt_non_classification_validations

    return PROTOCOL_VALIDATIONS[protocol]


def _is_dry_submit(validation):
    return isinstance(validation.validator, DrySubmitValidator)


def _run_validations(record, record_serializer, request, skip_dry_submit=False):
    validations = _get_protocol_validations(record)
    if skip_dry_submit:
        validations = [v for v in validations if not _is_dry_submit(v)]

    runner = ValidationRunner(serializer=record_serializer)
    runner.validate(record, validations, request=request)
    return runner


def _set_write_error_validation(runner, collect_record, request, write_result):
    """
    submit_collect_records() skips the dry submit validation and relies on the
    real write instead, so a failed write is recorded as a failed dry submit.
    """
    for validation in _get_protocol_validations(collect_record):
        if _is_dry_submit(validation):
            runner.add_result(
                dataclasses.replace(validation), collect_record, request, write_result=write_result
            )


def _apply_validation_suppressants(results, validation_suppressants):
    for identifier, validation_keys in validation_suppressants.items():
        results[identifier] = results.get(identifier) or dict()
        for validation_key in validation_keys:
            results[identifier][validation_key] = {"status": IGNORE, "messages": ""}

    return results


def check_validation_status(results):
    status = OK
    for validations in results.values():
        for check in validations.values():
            check_status = check.get("status")
            if check_status == ERROR:
                return ERROR
            elif check_status == WARN:
                status = WARN

    return status


@tracer.start_as_current_span("save_validation_output")
def _save_validation_output(profile, record, serializer_class, validation_output):
    stage = CollectRecord.SAVED_STAGE
    status = validation_output["status"]
    if status == OK:
        stage = CollectRecord.VALIDATED_STAGE

    validation_timestamp = timezone.now()
    validation_output["last_validated"] = str(validation_timestamp)
    serialized_collect_record = None
    collect_record = None

    qry = CollectRecord.objects.filter(id=record.pk)
    # Using update so updated_on and validation_timestamp matches
    qry.update(
        stage=stage,
        validations=validation_output,
        updated_on=validation_timestamp,
        updated_by=profile,
    )
    if qry.count() > 0:
        collect_record = qry[0]
        serialized_collect_record = serializer_class(collect_record).data

    return dict(status=status, record=serialized_collect_record)


def validate_collect_record(
    profile, record, serializer_class, validation_suppressants=None, trace_attributes=None
):
    trace_attributes = trace_attributes or RecordTraceAttributes()
    with tracer.start_as_current_span("validate_collect_record") as span:
        trace_attributes.add(span, record)
        request = MockRequest(profile=profile)
        validation_output = _run_validations(record, serializer_class, request).to_dict()
        if validation_suppressants:
            print("validation_suppressants not supported")

        return _save_validation_output(profile, record, serializer_class, validation_output)


def validate_collect_records(profile, record_ids, serializer_class, validation_suppressants=None):
    output = {}
    for record_id in record_ids:
        check_uuid(record_id)

    trace_attributes = RecordTraceAttributes()
    records = CollectRecord.objects.filter(id__in=record_ids)
    for record in records.iterator():
        output[str(record.pk)] = validate_collect_record(
            profile, record, serializer_class, validation_suppressants, trace_attributes
        )

    return output


def submit_collect_records(profile, record_ids, serializer_class, validation_suppressants=None):
    output = {}
    request = MockRequest(profile=profile)
    trace_attributes = RecordTraceAttributes()
    for record_id in record_ids:
        collect_record = CollectRecord.objects.get_or_none(id=record_id)
        if collect_record is None:
            output[record_id] = dict(status=ERROR, message=gettext_lazy("Not found"))
            continue

        with tracer.start_as_current_span("submit_collect_record") as span:
            trace_attributes.add(span, collect_record)
            output[record_id] = _submit_collect_record(
                profile,
                record_id,
                collect_record,
                serializer_class,
                request,
                validation_suppressants,
            )

    return output


def _submit_collect_record(
    profile, record_id, collect_record, serializer_class, request, validation_suppressants
):
    if validation_suppressants:
        print("validation_suppressants not supported")

    # The real write below runs the same writer in a savepoint and rolls
    # back on failure, so a dry submit here would only duplicate it.
    runner = _run_validations(collect_record, serializer_class, request, skip_dry_submit=True)
    validation_output = _save_validation_output(
        profile, collect_record, serializer_class, runner.to_dict()
    )
    status = validation_output["status"]

    if status != OK:
        return validation_output

    # If validate comes out all good (status == OK) then
    # try parsing and saving the collect record into its
    # components.
    try:
        status, result = write_collect_record(collect_record, request)
    except Exception as err:
        # Anything write_collect_record doesn't handle itself, e.g. a
        # statement timeout. The record must not be left VALIDATED.
        logger.exception(f"submit_collect_records: {record_id}")
        status, result = ERROR_STATUS, format_exception_errors(err)

    if status == SUCCESS_STATUS:
        return dict(status=OK, message=gettext_lazy("Success"))

    _set_write_error_validation(runner, collect_record, request, (status, result))
    validation_output = _save_validation_output(
        profile, collect_record, serializer_class, runner.to_dict()
    )

    if status == VALIDATION_ERROR_STATUS:
        message = result
    else:
        logger.error(json.dumps(dict(id=record_id, data=collect_record.data)), result)
        message = gettext_lazy("System failure")
    return dict(status=ERROR, message=message, record=validation_output["record"])
