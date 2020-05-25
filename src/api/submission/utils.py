import logging
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from django.core.exceptions import ValidationError as DJValidationError
from .writer import (
    BenthicLITProtocolWriter,
    BenthicPITProtocolWriter,
    FishbeltProtocolWriter,
    HabitatComplexityProtocolWriter,
    BleachingQuadratCollectionProtocolWriter,
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
            output[identifier] = [r.get("message") for r in record]
    else:
        output["exception"] = validationerror.messages
    return output


def format_exception_errors(err):
    identifier = '{}'.format(str(type(err).__name__))
    msg = ''
    if hasattr(err, 'message'):
        msg = err.message
    elif err.args:
        msg = ['; '.join(err.args)]
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
            logger.exception("write_collect_record: {}".format(getattr(collect_record, 'id')))
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
            validations=validations,
            updated_on=validation_timestamp
        )
