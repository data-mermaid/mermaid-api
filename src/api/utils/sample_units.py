import operator

from ..models import (
    BENTHICLIT_PROTOCOL,
    BENTHICPIT_PROTOCOL,
    BLEACHINGQC_PROTOCOL,
    FISHBELT_PROTOCOL,
    HABITATCOMPLEXITY_PROTOCOL,
    SampleEvent,
    SampleUnit,
    TransectMethod,
)
from . import get_subclasses


def delete_orphaned_sample_unit(su, deleted_tm=None):
    deleted = False
    tm_count = None
    # have to make sure there aren't other transect methods of *any* type left for this sample unit
    for tmclass in get_subclasses(TransectMethod):
        # Depends on OneToOne relationship, and `related_name` must end in '_method'
        tm = "{}_method".format(tmclass._meta.model_name)
        if hasattr(su, tm):
            if tm_count is None:
                tm_count = 0
            if not deleted_tm or (
                deleted_tm and not type(deleted_tm.subclass) == tmclass
            ):
                tm_count += 1

    if tm_count == 0:
        su.delete()
        deleted = True

    return deleted


def delete_orphaned_sample_event(se, deleted_su=None):
    deleted = False
    su_count = 0
    # have to make sure there aren't other SUs of *any* type left for this SE
    for suclass in get_subclasses(SampleUnit):
        sus = "{}_set".format(suclass._meta.model_name)
        su_set = operator.attrgetter(sus)(se)
        if deleted_su:
            su_count += su_set.exclude(pk=deleted_su.pk).count()
        else:
            su_count += su_set.all().count()

    if su_count == 0:
        se.delete()
        deleted = True

    return deleted


def find_bpfb_same_sample_event():
    for se in SampleEvent.objects.all():
        if (
            se.benthictransect_set.all().count() > 1
            and se.fishbelttransect_set.all().count() > 1
        ):
            print(se.pk)
            break


def migrate_collect_record_sample_event(collect_record):
    sample_event = collect_record.data.get("sample_event") or dict()

    if isinstance(sample_event, str):
        return

    protocol = collect_record.data.get("protocol")

    migration_fields = [
        "sample_time",
        "depth",
        "visibility",
        "current",
        "relative_depth",
        "tide",
    ]

    if protocol in (
        BENTHICLIT_PROTOCOL,
        BENTHICPIT_PROTOCOL,
        HABITATCOMPLEXITY_PROTOCOL,
    ):
        sample_unit_attribute = "benthic_transect"
    elif protocol == FISHBELT_PROTOCOL:
        sample_unit_attribute = "fishbelt_transect"
        pass
    elif protocol == BLEACHINGQC_PROTOCOL:
        sample_unit_attribute = "quadrat_collection"
    else:
        return

    sample_event_data = collect_record.data.get("sample_event") or dict()

    migrated_data = dict()
    for migration_field in migration_fields:
        migrated_data["migration_field"] = sample_event_data.get(migration_field)

    collect_record.data[sample_unit_attribute] = (
        collect_record.data.get(sample_unit_attribute) or dict()
    )
    collect_record.data[sample_unit_attribute].update(migrated_data)

    se_data = dict(
        management_id=sample_event_data.get("management"),
        site_id=sample_event_data.get("site"),
        sample_date=sample_event_data.get("sample_date"),
        notes=sample_event_data.get("notes") or "",
    )

    sample_events = SampleEvent.objects.filter(**se_data)
    if sample_events.count() > 0:
        se = sample_events[0]
    else:
        se = SampleEvent(**se_data)

    collect_record.data["sample_event"] = str(se.pk)
