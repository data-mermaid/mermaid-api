from api.models import (
    CollectRecord,
    Revision,
)
from api.resources.sync.pull import get_records, serialize_revisions
from api.resources.collect_record import CollectRecordSerializer


def test_get_records(db_setup, project1, profile1):
    collect_record = CollectRecord.objects.create(
        project=project1, profile=profile1, data=dict()
    )
    collect_record_id = collect_record.id

    collect_record.save()
    CollectRecord.objects.create(project=project1, profile=profile1, data=dict())

    recs = get_records(
        CollectRecord,
        None,
        collect_record.project_id,
        collect_record.profile_id,
    )

    assert len(recs) == 2

    rev_rec = Revision.objects.filter(table_name="api_collectrecord").order_by(
        "-revision_num"
    )[0]
    revision_num = rev_rec.revision_num
    updated_on = rev_rec.updated_on
    project_id = collect_record.project_id
    profile_id = collect_record.profile_id

    collect_record.delete()

    recs = get_records(
        CollectRecord,
        revision_num,
        project_id,
        profile_id
    )

    assert len(recs) == 1
    assert recs[0].revision_deleted is True


def test_serialize_revision_records(
    db_setup, collect_record_revision_with_updates, project1, profile1
):
    rec_rev = collect_record_revision_with_updates

    recs = get_records(CollectRecord, None, rec_rev.project_id, rec_rev.profile_id)
    serialized_records = serialize_revisions(CollectRecordSerializer, recs)

    assert len(serialized_records["updates"]) == 1
    assert len(serialized_records["deletes"]) == 1
    assert serialized_records["last_revision_num"] == recs[0].revision_revision_num

    CollectRecord.objects.create(
        project=project1, profile=profile1, data=dict(protocol="fishbelt")
    )

    recs2 = get_records(
        CollectRecord,
        revision_num=rec_rev.revision_num,
        project=rec_rev.project_id,
        profile=rec_rev.profile_id
    )

    serialized_records = serialize_revisions(CollectRecordSerializer, recs2)

    assert len(serialized_records["updates"]) == 2
    assert len(serialized_records["deletes"]) == 1
    assert serialized_records["last_revision_num"] == recs2[0].revision_revision_num

    # import json
    # from rest_framework.utils.encoders import JSONEncoder
    # print(json.dumps(serialized_records, indent=4, cls=JSONEncoder))
    # assert False
