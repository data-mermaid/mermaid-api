from collections import defaultdict

from django.core.exceptions import ObjectDoesNotExist
from django.db.models.deletion import ProtectedError
from django.forms.models import model_to_dict

from api.models import Project, Revision, SampleEvent
from api.resources.sampleunitmethods.sample_unit_methods import SampleUnitMethodView
from api.utils.sample_unit_methods import get_project
from ...utils.project import delete_project
from ...utils.q import submit_job
from .utils import ViewRequest


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


def _get_sumethods(request, se):
    project = get_project(se, se.project_lookup.split("__"))
    vw_request = ViewRequest(user=request.user, headers=request.headers, method="GET")
    vw_request.META = request.META
    vw_request.authenticators = request.authenticators
    vw_request.successful_authenticator = request.successful_authenticator

    viewset = SampleUnitMethodView(request=vw_request, format_kwarg=None)
    queryset = viewset.limit_to_project(vw_request, project_pk=project.pk)
    serializer = viewset.get_serializer(queryset, many=True)

    return [sumethod for sumethod in serializer.data if sumethod.get("sample_event") == str(se.pk)]


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
    :return: Status code, message, and errors [optional]. Use 418 for special cases.
    :rtype: tuple
    """
    is_deleted = record.get("_deleted") is True
    record_id = record.get("id")
    model_class = serializer.Meta.model

    if is_deleted:
        try:
            instance = model_class.objects.get(pk=record_id)

            # If deleting a project, deliberately delete all protected objects!
            if model_class == Project:
                submit_job(0, True, delete_project, record_id)
                Revision.create_from_instance(instance, deleted=True)
                return 202, "Project has been flagged for deletion", None

            instance.delete()

        except ProtectedError as err:
            protected_objects = defaultdict(list)
            if hasattr(err, "protected_objects"):
                for obj in err.protected_objects:
                    protected_model = obj._meta.model_name
                    protected_obj = model_to_dict(obj)
                    protected_objects[protected_model].append(protected_obj)

                    if isinstance(obj, SampleEvent):
                        sumethods = _get_sumethods(request, obj)
                        for sumethod in sumethods:
                            sumethod_model = sumethod.get("protocol", "undefined_method")
                            protected_objects[sumethod_model].append(sumethod)
            return 418, "Protected Objects", protected_objects

        except ObjectDoesNotExist:
            return (
                404,
                "Does Not Exist",
                f"{model_class._meta.model_name.capitalize()} with id {record_id} does not exist to delete",
            )

        return 204, "", None

    instance = None
    last_revision_num = record.get("_last_revision_num")
    if force is False and _has_push_conflict(record_id, last_revision_num):
        return 409, "Conflict", None

    if last_revision_num is not None:
        try:
            instance = model_class.objects.get(pk=record_id)
        except ObjectDoesNotExist:
            return (
                404,
                "Does Not Exist",
                f"{model_class._meta.model_name.capitalize()} with id {record_id} does not exist",
            )

        status_code = 200
    else:
        status_code = 201

    s = serializer(instance=instance, data=record, context={"request": request})

    if s.is_valid() is False:
        return 400, "Validation Error", s.errors

    s.save()

    return status_code, "", None
