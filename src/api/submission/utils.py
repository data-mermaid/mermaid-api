import json
import logging

from django.core.exceptions import ValidationError as DJValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.translation import ugettext_lazy
from rest_framework.exceptions import ValidationError

from ..mocks import MockRequest
from ..models import CollectRecord
from .protocol_validations import (
    BenthicLITProtocolValidation,
    BenthicPITProtocolValidation,
    BleachingQuadratCollectionProtocolValidation,
    FishBeltProtocolValidation,
    HabitatComplexityProtocolValidation,
)
from .validations import ERROR, IGNORE, OK, WARN
from .writer import (
    BenthicLITProtocolWriter,
    BenthicPITProtocolWriter,
    BleachingQuadratCollectionProtocolWriter,
    FishbeltProtocolWriter,
    HabitatComplexityProtocolWriter,
)

BENTHICLIT_PROTOCOL = "benthiclit"
BENTHICPIT_PROTOCOL = "benthicpit"
BLEACHING_QC_PROTOCOL = "bleachingqc"
FISHBELT_PROTOCOL = "fishbelt"
HABITATCOMPLEXITY_PROTOCOL = "habitatcomplexity"
PROTOCOLS = (
    BENTHICLIT_PROTOCOL,
    BENTHICPIT_PROTOCOL,
    BLEACHING_QC_PROTOCOL,
    FISHBELT_PROTOCOL,
    HABITATCOMPLEXITY_PROTOCOL,
)


SUCCESS_STATUS = 200
VALIDATION_ERROR_STATUS = 400
ERROR_STATUS = 500

logger = logging.getLogger(__name__)


def get_writer(collect_record, context):
    protocol = collect_record.data.get("protocol")
    if protocol not in PROTOCOLS:
        return None

    if protocol == BENTHICLIT_PROTOCOL:
        return BenthicLITProtocolWriter(collect_record, context)

    elif protocol == BENTHICPIT_PROTOCOL:
        return BenthicPITProtocolWriter(collect_record, context)

    elif protocol == FISHBELT_PROTOCOL:
        return FishbeltProtocolWriter(collect_record, context)

    elif protocol == HABITATCOMPLEXITY_PROTOCOL:
        return HabitatComplexityProtocolWriter(collect_record, context)

    elif protocol == BLEACHING_QC_PROTOCOL:
        return BleachingQuadratCollectionProtocolWriter(collect_record, context)


def format_serializer_errors(validationerror):
    output = dict()
    if hasattr(validationerror, "get_full_details"):
        details = validationerror.get_full_details()
        for identifier, record in details.items():
            output[identifier] = [str(r.get("message")) for r in record]
    else:
        output["exception"] = validationerror.messages
    return output


def format_exception_errors(err):
    identifier = "{}".format(str(type(err).__name__))
    msg = ""
    if hasattr(err, "message"):
        msg = err.message
    elif err.args:
        msg = ["; ".join(err.args)]
    return {identifier: [msg]}


def write_collect_record(collect_record, request, dry_run=False):
    status = None
    result = None
    context = {"request": request}
    writer = get_writer(collect_record, context)
    with transaction.atomic():
        sid = transaction.savepoint()
        try:
            writer.write()
            status = SUCCESS_STATUS
        except (ValidationError, DJValidationError) as ve:
            result = format_serializer_errors(ve)
            status = VALIDATION_ERROR_STATUS
        except Exception as err:
            logger.exception(
                "write_collect_record: {}".format(getattr(collect_record, "id"))
            )
            result = format_exception_errors(err)
            status = ERROR_STATUS
        finally:
            if dry_run is True or status != SUCCESS_STATUS:
                transaction.savepoint_rollback(sid)
            else:
                collect_record.delete()
                transaction.savepoint_commit(sid)
        return status, result


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


def _validate_collect_record(record, request):
    protocol = record.data.get("protocol")
    if protocol not in PROTOCOLS:
        raise ValueError(ugettext_lazy(f"{protocol} not supported"))

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


def validate_collect_records(
    profile, record_ids, serializer_class, validation_suppressants=None
):
    output = dict()
    records = CollectRecord.objects.filter(id__in=record_ids)
    request = MockRequest(profile=profile)
    for record in records.iterator():
        status, validation_output = _validate_collect_record(record, request)

        if validation_suppressants:
            validation_output = _apply_validation_suppressants(
                validation_output, validation_suppressants
            )
            status = check_validation_status(validation_output)

        stage = CollectRecord.SAVED_STAGE
        if status == OK:
            stage = CollectRecord.VALIDATED_STAGE

        validation_timestamp = timezone.now()
        validations = dict(
            status=status,
            results=validation_output,
            last_validated=str(validation_timestamp),
        )
        serialized_collect_record = None
        collect_record = None

        qry = CollectRecord.objects.filter(id=record.pk)
        # Using update so updated_on and validation_timestamp matches
        qry.update(
            stage=stage,
            validations=validations,
            updated_on=validation_timestamp,
            updated_by=profile,
        )
        if qry.count() > 0:
            collect_record = qry[0]
            serialized_collect_record = serializer_class(collect_record).data
        output[str(record.pk)] = dict(status=status, record=serialized_collect_record)

    return output


def submit_collect_records(profile, record_ids, validation_suppressants=None):
    output = {}
    request = MockRequest(profile=profile)
    for record_id in record_ids:
        collect_record = CollectRecord.objects.get_or_none(id=record_id)
        if collect_record is None:
            output[record_id] = dict(status=ERROR, message=ugettext_lazy("Not found"))
            continue

        status, validation_output = _validate_collect_record(collect_record, request)
        if validation_suppressants:
            validation_output = _apply_validation_suppressants(
                validation_output, validation_suppressants
            )
            status = check_validation_status(validation_output)

        if status != OK:
            output[record_id] = dict(
                status=status, message=ugettext_lazy("Invalid collect record")
            )
            continue

        # If validate comes out all good (status == OK) then
        # try parsing and saving the collect record into its
        # components.
        status, result = write_collect_record(collect_record, request)
        if status == VALIDATION_ERROR_STATUS:
            output[record_id] = dict(status=ERROR, message=result)
            continue
        elif status == ERROR_STATUS:
            logger.error(
                json.dumps(dict(id=record_id, data=collect_record.data)), result
            )
            output[record_id] = dict(
                status=ERROR, message=ugettext_lazy("System failure")
            )
            continue
        output[record_id] = dict(status=OK, message=ugettext_lazy("Success"))

    return output
