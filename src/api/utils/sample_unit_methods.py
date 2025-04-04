import uuid

from django.db import transaction

from ..mocks import MockRequest
from ..models import AuditRecord


def get_project(obj, keys):
    if not keys:
        return obj

    new_obj = getattr(obj, keys[0])
    return get_project(new_obj, keys[1:])


def add_protected_data(instance, k, v):
    decorated_v = v
    if k == "observers":
        observers = {str(o.id): o for o in instance.observers.select_related("profile")}
        for serialized_observer in decorated_v:
            serialized_observer["email"] = observers[serialized_observer["id"]].profile.email

    return decorated_v


def transect_method_to_collect_record(serializer, transect_method_instance, profile, protocol):
    from api.resources.collect_record import CollectRecordSerializer

    request = MockRequest(profile=profile)

    if transect_method_instance is None:
        raise TypeError("instance is None")

    skip_fields = (
        "created_on",
        "updated_on",
        "created_by",
        "updated_by",
    )

    project = get_project(
        transect_method_instance, transect_method_instance.project_lookup.split("__")
    )

    data = serializer(instance=transect_method_instance).data
    record = {
        "id": transect_method_instance.collect_record_id or str(uuid.uuid4()),
        "stage": CollectRecordSerializer.Meta.model.SAVED_STAGE,
        "project": str(project.pk),
        "profile": str(profile.pk),
        "data": {"protocol": protocol, "sample_unit_method_id": str(transect_method_instance.pk)},
    }

    for k, v in data.items():
        if k in skip_fields:
            record[k] = v
        else:
            record["data"][k] = add_protected_data(transect_method_instance, k, v)

    cr = CollectRecordSerializer(data=record, context={"request": request})
    cr.is_valid(raise_exception=True)
    return cr.save()


def create_audit_record(profile, event_type, record):
    return AuditRecord.objects.create(
        event_type=event_type,
        event_by=profile,
        model=record._meta.model.__name__.lower(),
        record_id=record.pk,
    )


@transaction.atomic
def edit_transect_method(serializer_class, collect_record_owner, request, pk, protocol):
    instance = serializer_class.Meta.model.objects.get(id=pk)
    collect_record = transect_method_to_collect_record(
        serializer_class, instance, collect_record_owner, protocol
    )
    create_audit_record(request.user.profile, AuditRecord.EDIT_RECORD_EVENT_TYPE, instance)
    instance.delete()

    return collect_record
