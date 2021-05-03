from django.core.exceptions import ObjectDoesNotExist

from api.models import Revision


def get_request_method(record):
    """Determine the request method based on the record's edits.

    :param record: Edits record.
    :type record: dict
    :return: Request method
    :rtype: str
    """
    if record.get("_deleted") is True:
        return "DELETE"
    elif record.get("_last_revision_num") is None:
        return "POST"
    else:
        return "PUT"


def _has_push_conflict(record_id, last_revision_num):
    """Check if record would have a conflict if edits
    were applied.

    :param record_id: Id of the record with edits.
    :type record_id: str
    :param last_revision_num:
    :type last_revision_num: int or None
    :return: True if there's a conflict.
    :rtype: bool
    """
    if last_revision_num is None:
        return False

    try:
        rev = Revision.objects.get(record_id=record_id)
    except ObjectDoesNotExist:
        return False

    return rev.revision_num > last_revision_num


def apply_changes(request, serializer, record, force=False):
    """Create, update or delete record.

    :param request: Generated django request or supplied ViewRequest created.  Request's method
    should be set based on the edit being applied (PUT, POST, DELETE).
    :type request: rest_framework.requests.Request or api.resources.sync.view.ViewRequest
    :param serializer: Serializer for deserializing record. example: CollectRecordSerializer
    :type serializer: rest_framework.serializers.ModelSerializer
    :param record: Serialized record
    :type record: dict
    :param force: Ignore conflicts and apply change, defaults to False
    :type force: bool, optional
    :return: Status code and errors [optional]
    :rtype: tuple
    """
    is_deleted = record.get("_deleted") is True
    record_id = record.get("id")
    model_class = serializer.Meta.model
    if is_deleted:
        try:
            model_class.objects.get(pk=record_id).delete()
        except ObjectDoesNotExist:
            pass

        return 204, None

    instance = None
    last_revision_num = record.get("_last_revision_num")
    if force is False and _has_push_conflict(record_id, last_revision_num):
        return 409, None

    if last_revision_num is not None:
        instance = model_class.objects.get(pk=record_id)
        status_code = 200
    else:
        status_code = 201

    s = serializer(instance=instance, data=record, context={"request": request})

    if s.is_valid() is False:
        return 400, s.errors

    s.save()

    return status_code, None
