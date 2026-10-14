import uuid

import pytest
from rest_framework.exceptions import ParseError

from api.mocks import MockRequest
from api.models import CollectRecord, Project, ProjectProfile, Revision
from api.resources.collect_record import CollectRecordSerializer, CollectRecordViewSet
from api.resources.project import ProjectViewSet
from api.resources.sync.pull import _get_records, get_records, serialize_revisions
from api.resources.sync.views import _get_required_parameters


def test_get_required_parameters_rejects_non_integer_revision_num():
    # get_records() interpolates revision_num into raw SQL (revision.revision_num > {..}),
    # so this is a SQL injection guard, not just input validation.
    request = MockRequest(profile=None)
    with pytest.raises(ValueError):
        _get_required_parameters(
            request, {"last_revision": "0 OR 1=1", "project": str(uuid.uuid4())}, ("project",)
        )


def test_get_required_parameters_rejects_non_uuid_project():
    # Same raw-SQL concern as above, for revision.project_id = '{..}'::uuid.
    request = MockRequest(profile=None)
    with pytest.raises(ParseError):
        _get_required_parameters(
            request, {"last_revision": "5", "project": "x' OR '1'='1"}, ("project",)
        )


def test_get_records_project_profile_prefilter_in_isolation(
    db_setup, project1, project2, profile1, profile2
):
    # Isolates the queryset-level pre-filter added to _get_records() (pull.py) from the
    # pre-existing revision.project_id/profile_id filters that get_records() normally also
    # applies -- those alone would already exclude the "other" records below, which is why
    # test_get_records() (further down) doesn't actually prove this filter does anything.
    # Here, filters carries no project/profile condition at all, so if the pre-filter were a
    # no-op (e.g. CollectRecord.project_lookup got renamed), these "other" records would leak.
    request = MockRequest(profile=profile1)
    viewset = CollectRecordViewSet(request=request)

    mine = CollectRecord.objects.create(project=project1, profile=profile1, data=dict())
    CollectRecord.objects.create(project=project1, profile=profile2, data=dict())
    CollectRecord.objects.create(project=project2, profile=profile1, data=dict())

    updates, deletes, removes = _get_records(
        viewset,
        profile1.pk,
        filters=["revision.table_name = 'api_collectrecord'"],
        rp_project=project1.pk,
        rp_profile=profile1.pk,
    )

    assert {u.id for u in updates} == {mine.id}


def test_get_records(db_setup, project1, project2, project3, profile1, profile2, project_profile1):
    request = MockRequest(profile=profile1)
    collect_record_viewset = CollectRecordViewSet(request=request)
    project_viewset = ProjectViewSet(request=request)

    # Create new revision
    collect_record = CollectRecord.objects.create(project=project1, profile=profile1, data=dict())

    # This should NOT create a revision
    collect_record.save()

    # Create new revision
    CollectRecord.objects.create(project=project1, profile=profile1, data=dict())

    # Other project/profile combos: must not leak into a project1+profile1 pull.
    # _get_records() pre-filters the queryset by project_lookup/profile_id before
    # the revision join now (src/api/resources/sync/pull.py) -- this would also
    # have been excluded by the join alone, so this guards against a regression in
    # that new, separate filter rather than the join's pre-existing scoping.
    CollectRecord.objects.create(project=project1, profile=profile2, data=dict())
    CollectRecord.objects.create(project=project2, profile=profile1, data=dict())

    for rev in Revision.objects.all():
        print(
            f"[{rev.revision_num}] {rev.table_name} {rev.record_id} {rev.deleted} {rev.related_to_profile_id}"
        )

    updates, deletes, removes = get_records(
        collect_record_viewset,
        profile1.pk,
        required_params={
            "revision_num": None,
            "project": collect_record.project_id,
            "profile": collect_record.profile_id,
        },
    )

    assert len(updates) == 2
    assert len(deletes) == 0

    rev_rec = Revision.objects.filter(table_name="api_collectrecord").order_by("-revision_num")[0]
    revision_num = rev_rec.revision_num
    project_id = collect_record.project_id
    profile_id = collect_record.profile_id

    collect_record.delete()

    updates, deletes, removes = get_records(
        collect_record_viewset,
        profile1.pk,
        required_params={
            "revision_num": revision_num,
            "project": project_id,
            "profile": profile_id,
        },
    )

    assert len(updates) == 0
    assert len(deletes) == 1

    updates, deletes, removes = get_records(project_viewset, profile1.pk, required_params=None)

    assert len(updates) == 1
    assert len(deletes) == 0


def test_serialize_revision_records(
    db_setup, collect_record_revision_with_updates, project1, profile1
):
    request = MockRequest(profile=profile1)
    collect_record_viewset = CollectRecordViewSet(request=request)
    rec_rev = collect_record_revision_with_updates

    updates, deletes, removes = get_records(
        collect_record_viewset,
        profile1.pk,
        {"revision_num": None, "project": rec_rev.project_id, "profile": rec_rev.profile_id},
    )
    serialized_records = serialize_revisions(CollectRecordSerializer, updates, deletes, removes)

    rev_nums = [u.revision_revision_num for u in updates]
    rev_nums.extend([d["revision_num"] for d in deletes])
    check_rev_num = max(rev_nums)

    assert len(serialized_records["updates"]) == 1
    assert len(serialized_records["deletes"]) == 1
    assert len(serialized_records["removes"]) == 0
    assert serialized_records["last_revision_num"] == check_rev_num

    CollectRecord.objects.create(project=project1, profile=profile1, data=dict(protocol="fishbelt"))

    updates2, deletes2, removes2 = get_records(
        collect_record_viewset,
        profile1.pk,
        {
            "revision_num": rec_rev.revision_num,
            "project": rec_rev.project_id,
            "profile": rec_rev.profile_id,
        },
    )

    serialized_records = serialize_revisions(CollectRecordSerializer, updates2, deletes2, removes2)

    rev_nums2 = [u.revision_revision_num for u in updates2]
    rev_nums2.extend([d["revision_num"] for d in deletes2])
    check_rev_num2 = max(rev_nums2)

    assert len(serialized_records["updates"]) == 2
    assert len(serialized_records["deletes"]) == 1
    assert len(serialized_records["removes"]) == 0
    assert serialized_records["last_revision_num"] == check_rev_num2


def test_added_to_project(db_setup, profile1):
    request = MockRequest(profile=profile1)
    project_viewset = ProjectViewSet(request=request)

    project2 = Project.objects.create(name="p2")
    project1 = Project.objects.create(name="p1")

    ProjectProfile.objects.create(project=project1, profile=profile1, role=ProjectProfile.COLLECTOR)

    updates, deletes, removes = get_records(project_viewset, profile1.pk, None)

    assert len(updates) == 1
    assert len(deletes) == 0
    assert len(removes) == 0

    revision_number = updates[0].revision_revision_num

    ProjectProfile.objects.create(project=project2, profile=profile1, role=ProjectProfile.COLLECTOR)

    updates, deletes, removes = get_records(
        project_viewset, profile1.pk, {"revision_num": revision_number}
    )

    assert len(updates) == 1
    assert len(deletes) == 0
    assert len(removes) == 0


def test_removed_from_project(db_setup, profile1, project_profile1):
    request = MockRequest(profile=profile1)
    project_viewset = ProjectViewSet(request=request)

    updates, deletes, removes = get_records(project_viewset, profile1.pk, None)

    assert len(updates) == 1
    assert len(deletes) == 0

    revision_number = updates[0].revision_revision_num

    project_profile1.delete()

    updates, deletes, removes = get_records(
        project_viewset, profile1.pk, {"revision_num": revision_number}
    )

    assert len(updates) == 0
    assert len(deletes) == 0
    assert len(removes) == 1


def test_added_removed_added_to_project(db_setup, project1, profile1):
    request = MockRequest(profile=profile1)
    project_viewset = ProjectViewSet(request=request)

    # Add
    project_profile1 = ProjectProfile.objects.create(
        project=project1, profile=profile1, role=ProjectProfile.COLLECTOR
    )
    # Delete
    project_profile1.delete()
    # Re-Add
    ProjectProfile.objects.create(project=project1, profile=profile1, role=ProjectProfile.COLLECTOR)

    updates, deletes, removes = get_records(project_viewset, profile1.pk, None)

    assert len(updates) == 1
    assert len(deletes) == 0
    assert len(removes) == 0


def test_create_delete_create_collect_record_pull(db_setup, project1, profile1):
    uid = uuid.uuid4()
    request = MockRequest(profile=profile1)
    cr_viewset = CollectRecordViewSet(request=request)

    updates, deletes, removes = get_records(cr_viewset, profile1.pk, None)
    assert len(updates) == 0
    assert len(deletes) == 0
    assert len(removes) == 0

    cr = CollectRecord.objects.create(id=uid, project=project1, profile=profile1, data=dict())
    assert uid == cr.id
    cr.data = {"protocol": "fishbelt"}
    cr.save()

    revision = Revision.objects.get(table_name="api_collectrecord", record_id=uid)

    cr.delete()

    cr = CollectRecord.objects.create(id=uid, project=project1, profile=profile1, data=dict())

    updates, deletes, removes = get_records(
        cr_viewset, profile1.pk, {"revision_num": revision.revision_num}
    )

    assert len(updates) == 1
    assert len(deletes) == 0
    assert len(removes) == 0
