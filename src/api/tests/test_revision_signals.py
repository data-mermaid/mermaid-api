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
