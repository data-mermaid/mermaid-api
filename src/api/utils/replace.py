from django.db.models import Q
from django.utils import timezone

from api.models.revisions import Revision
from ..models import CollectRecord, SampleEvent


def replace_sampleunit_objs(find_objs, replace_obj, field, profile):
    replace_counts = {
        "num_sample_events_updated": 0,
        "num_collect_records_updated": 0,
        "num_{}s_removed".format(field): 0,
    }

    if not find_objs:
        return replace_counts

    updated_on = timezone.now()

    sample_events = SampleEvent.objects.filter(**{"{}__in".format(field): find_objs})
    replace_counts["num_sample_events_updated"] = sample_events.count()
    sample_events.update(
        **{
            "updated_on": updated_on,
            "updated_by": profile,
            "{}_id".format(field): replace_obj.id,
        }
    )

    qry_filter = Q()
    for obj in find_objs:
        qry_filter |= Q(**{"data__sample_event__{}".format(field): obj.id})

    collect_records = CollectRecord.objects.filter(qry_filter)
    replace_counts["num_collect_records_updated"] = collect_records.count()
    for collect_record in collect_records:
        collect_record.data["sample_event"][field] = replace_obj.id
        collect_record.save()

    # Before sites are removed, their notes are transferred to the
    # site that is being kept.
    notes = [replace_obj.notes] if replace_obj.notes else []
    for obj in find_objs:
        if obj.notes:
            notes.append(obj.notes)
        replace_counts["num_{}s_removed".format(field)] += 1
        obj.delete()

    replace_obj.notes = "\n\n".join(notes)
    replace_obj.save()

    return replace_counts


def replace_collect_record_owner(project_id, from_profile, to_profile, updated_by):
    updated_on = timezone.now()
    # replace_collect_record_owner will be called in a transaction, so when we
    # query collect records we also lock them until the end of the transaction
    # in order to prevent conflicts.
    collect_records = CollectRecord.objects.select_for_update().filter(
        project_id=project_id, profile=from_profile
    )
    num_collect_records_updated = collect_records.count()

    new_collect_records = []
    for collect_record in collect_records:
        Revision.create_from_instance(
            instance=collect_record,
            profile_id=from_profile.pk,
            deleted=False,
            related_to_profile_id=from_profile.pk,
        )
        Revision.remove_from_instance(
            instance=collect_record,
            profile_id=to_profile.pk,
            deleted=False,
            related_to_profile_id=to_profile.pk,
        )

        collect_record.pk = None
        collect_record.profile = to_profile
        collect_record.updated_on = updated_on
        collect_record.updated_by = updated_by

        new_collect_records.append(collect_record)

    CollectRecord.objects.bulk_create(new_collect_records)
    collect_records.delete()

    # Trigger new revision for project profiles
    from_project_profile = from_profile.projects.get(project_id=project_id)
    to_project_profile = to_profile.projects.get(project_id=project_id)
    Revision.create_from_instance(from_project_profile)
    Revision.create_from_instance(to_project_profile)

    return num_collect_records_updated
