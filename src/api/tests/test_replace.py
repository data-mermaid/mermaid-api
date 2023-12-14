from api.models import Revision
from api.utils.replace import replace_collect_record_owner


def test_replace_collect_record_owner(
    base_project,
    collect_record1,
    profile1,
    profile2,
    project_profile1,
):
    table_name = project_profile1._meta.db_table
    project_id = project_profile1.project.pk

    last_project_profile_revision_num = Revision.objects.filter(
        table_name=table_name, project_id=project_id
    ).order_by("-revision_num")[0]

    num_collect_records_updated = replace_collect_record_owner(
        project_id=collect_record1.project.pk,
        from_profile=profile1,
        to_profile=profile2,
        updated_by=profile1,
    )

    new_project_profile_revision_num = Revision.objects.filter(
        table_name=table_name, project_id=project_id
    ).order_by("-revision_num")[0]

    assert num_collect_records_updated == 1
    assert last_project_profile_revision_num < new_project_profile_revision_num
