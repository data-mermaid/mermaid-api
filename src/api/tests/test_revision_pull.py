from api.mocks import MockRequest
from api.models import (
    CollectRecord,
    Project,
    ProjectProfile,
    Revision,
)
from api.resources.sync.pull import get_records, serialize_revisions
from api.resources.collect_record import CollectRecordSerializer, CollectRecordViewSet
from api.resources.project import ProjectSerializer, ProjectViewSet


def test_get_records(db_setup, project1, project2, project3, profile1, project_profile1):
    request = MockRequest(profile=profile1)
    collect_record_viewset = CollectRecordViewSet(request=request)
    project_viewset = ProjectViewSet(request=request)

    collect_record = CollectRecord.objects.create(
        project=project1, profile=profile1, data=dict()
    )

    collect_record.save()
    CollectRecord.objects.create(project=project1, profile=profile1, data=dict())

    updates, deletes = get_records(
        collect_record_viewset,
        None,
        collect_record.project_id,
        collect_record.profile_id,
    )

    assert len(updates) == 2
    assert len(deletes) == 0

    rev_rec = Revision.objects.filter(table_name="api_collectrecord").order_by(
        "-revision_num"
    )[0]
    revision_num = rev_rec.revision_num
    project_id = collect_record.project_id
    profile_id = collect_record.profile_id

    collect_record.delete()

    updates, deletes = get_records(
        collect_record_viewset,
        revision_num,
        project_id,
        profile_id
    )

    assert len(updates) == 0
    assert len(deletes) == 1

    updates, deletes = get_records(
        project_viewset,
        None
    )

    assert len(updates) == 1
    assert len(deletes) == 0


def test_serialize_revision_records(
    db_setup, collect_record_revision_with_updates, project1, profile1
):
    request = MockRequest(profile=profile1)
    collect_record_viewset = CollectRecordViewSet(request=request)
    rec_rev = collect_record_revision_with_updates

    updates, deletes = get_records(collect_record_viewset, None, rec_rev.project_id, rec_rev.profile_id)
    serialized_records = serialize_revisions(CollectRecordSerializer, updates, deletes)

    rev_nums = [u.revision_revision_num for u in updates]
    rev_nums.extend([d["revision_num"] for d in deletes])
    check_rev_num = max(rev_nums)

    assert len(serialized_records["updates"]) == 1
    assert len(serialized_records["deletes"]) == 1
    assert serialized_records["last_revision_num"] == check_rev_num

    CollectRecord.objects.create(
        project=project1, profile=profile1, data=dict(protocol="fishbelt")
    )

    updates2, deletes2 = get_records(
        collect_record_viewset,
        revision_num=rec_rev.revision_num,
        project=rec_rev.project_id,
        profile=rec_rev.profile_id
    )

    serialized_records = serialize_revisions(CollectRecordSerializer, updates2, deletes2)

    rev_nums2 = [u.revision_revision_num for u in updates2]
    rev_nums2.extend([d["revision_num"] for d in deletes2])
    check_rev_num2 = max(rev_nums2)

    assert len(serialized_records["updates"]) == 2
    assert len(serialized_records["deletes"]) == 1
    assert serialized_records["last_revision_num"] == check_rev_num2


def test_added_to_project(db_setup, profile1):
    request = MockRequest(profile=profile1)
    project_viewset = ProjectViewSet(request=request)

    project2 = Project.objects.create(name="p2")
    project1 = Project.objects.create(name="p1")

    ProjectProfile.objects.create(project=project1, profile=profile1, role=ProjectProfile.COLLECTOR)

    updates, deletes = get_records(
        project_viewset,
        None
    )

    assert len(updates) == 1
    assert len(deletes) == 0

    revision_number = updates[0].revision_revision_num

    ProjectProfile.objects.create(project=project2, profile=profile1, role=ProjectProfile.COLLECTOR)

    updates, deletes = get_records(
        project_viewset,
        revision_number
    )

    assert len(updates) == 1
    assert len(deletes) == 0


def test_removed_from_project(db_setup, profile1, project_profile1):
    request = MockRequest(profile=profile1)
    project_viewset = ProjectViewSet(request=request)

    updates, deletes = get_records(
        project_viewset,
        None
    )

    assert len(updates) == 1
    assert len(deletes) == 0

    revision_number = updates[0].revision_revision_num

    project_profile1.delete()

    updates, deletes = get_records(
        project_viewset,
        revision_number
    )

    assert len(updates) == 0
    assert len(deletes) == 0
