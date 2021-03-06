import operator
from django.db import transaction
from . import get_subclasses
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
        migrated_data[migration_field] = sample_event_data.get(migration_field)

    collect_record.data[sample_unit_attribute] = (
        collect_record.data.get(sample_unit_attribute) or dict()
    )
    collect_record.data[sample_unit_attribute].update(migrated_data)


def consolidate_sample_events(*args, dryrun=False):
    suclasses = get_subclasses(SampleUnit)

    with transaction.atomic():
        sid = transaction.savepoint()

        for se in SampleEvent.objects.all():
            se_pk = se.pk
            orphaned = delete_orphaned_sample_event(se)
            if orphaned:
                print('Deleted orphaned SE {}'.format(se_pk))
                continue

            dups = SampleEvent.objects.filter(
                site=se.site_id,
                management=se.management_id,
                sample_date=se.sample_date,
            ).exclude(pk=se_pk)

            if dups.count() > 0:
                print('Removing dups for {}'.format(se_pk))
                for d in dups:
                    try:
                        se2 = SampleEvent.objects.get(pk=se_pk)

                        for suclass in suclasses:
                            sus = suclass.objects.filter(sample_event=d.pk)
                            notes = d.notes or ""
                            if notes.strip():
                                se.notes += "\n\n{}".format(notes)
                                se.save()
                            sus.update(sample_event=se)  # no signals fired
                            print('Changed SE from {} to {}'.format(d.pk, se_pk))

                        print('Deleting SE {}'.format(d.pk))
                        d.delete()

                    except SampleEvent.DoesNotExist:
                        print('{} already deleted'.format(se_pk))

        if dryrun:
            transaction.savepoint_rollback(sid)
        else:
            transaction.savepoint_commit(sid)
