from copy import deepcopy

from api.models import AuthUser, Revision


def test_replace_collect_record_owner(
    base_project,
    collect_record1,
    profile1,
    project_profile1,
):
    base_revision_num = Revision.objects.get(record_id=project_profile1.pk)

    auth_user = AuthUser.objects.create(profile=profile1, user_id="some@id")

    revision_num = Revision.objects.get(record_id=project_profile1.pk)
    assert revision_num > base_revision_num

    base_revision_num = revision_num

    auth_user.delete()

    revision_num = Revision.objects.get(record_id=project_profile1.pk)
    assert revision_num > base_revision_num

    base_revision_num = revision_num

    profile1.first_name = "My name changed"
    profile1.save()
    revision_num = Revision.objects.get(record_id=project_profile1.pk)
    assert revision_num > base_revision_num

    base_revision_num = revision_num

    collect_record1.delete()
    revision_num = Revision.objects.get(record_id=project_profile1.pk)
    assert revision_num > base_revision_num


def _get_latest_proj_revision():
    revision_num = (
        Revision.objects.filter(table_name="project").order_by("-revision_num")[0].revision_num
    )
    return revision_num


def test_project_sites(site1):
    base_revision_num = _get_latest_proj_revision()

    # project is updated with # of sites when site created
    site2 = deepcopy(site1)
    site2.id = None
    site2.name = "site2"
    site2.save()
    revision_num = _get_latest_proj_revision()
    assert revision_num > base_revision_num

    # project is updated with # of sites when site deleted
    base_revision_num = revision_num
    site2.delete()
    revision_num = _get_latest_proj_revision()
    assert revision_num > base_revision_num
