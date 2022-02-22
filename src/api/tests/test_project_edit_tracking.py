from api.models import (
    FISHBELT_PROTOCOL,
    ProjectProfile,
    SummarySampleEventModel,
    SummarySiteModel,
)
from api.resources.sample_units.beltfishmethod import BeltFishMethodSerializer
from api.submission.utils import write_collect_record
from api.utils.sample_unit_methods import edit_transect_method
from api.utils.summaries import update_project_summaries


def test_project_edit_tracking(valid_collect_record, profile1_request):
    project_id = valid_collect_record.project_id
    write_collect_record(valid_collect_record, profile1_request)
    summary_site_count = SummarySiteModel.objects.filter(project_id=project_id).count()
    summary_se_count = SummarySampleEventModel.objects.filter(
        project_id=project_id
    ).count()

    assert summary_site_count == 1
    assert summary_se_count == 1


def test_edit_transect_method(
    belt_fish_project, belt_fish1, profile1, profile1_request
):
    project_id = belt_fish1.transect.sample_event.site.project_id

    update_project_summaries(project_id)

    summary_site_count = SummarySiteModel.objects.filter(project_id=project_id).count()
    summary_se_count = SummarySampleEventModel.objects.filter(
        project_id=project_id
    ).count()

    assert summary_site_count == 2
    assert summary_se_count == 2

    edit_transect_method(
        BeltFishMethodSerializer,
        profile1,
        profile1_request,
        belt_fish1.pk,
        FISHBELT_PROTOCOL,
    )

    summary_site_count = SummarySiteModel.objects.filter(project_id=project_id).count()
    summary_se_count = SummarySampleEventModel.objects.filter(
        project_id=project_id
    ).count()

    assert summary_site_count == 1
    assert summary_se_count == 1


def test_edit_site(belt_fish_project, site1):
    project_id = site1.project_id
    update_project_summaries(project_id)

    original_site_name = site1.name

    assert SummarySiteModel.objects.filter(site_name=original_site_name).exists()

    site1.name = "Changing my name"
    site1.save()

    assert (
        SummarySiteModel.objects.filter(site_name=original_site_name).exists() is False
    )
    assert SummarySiteModel.objects.filter(site_name=site1.name).exists()


def test_edit_management(belt_fish_project, management1):
    project_id = management1.project_id
    update_project_summaries(project_id)

    original_management_name = management1.name

    assert SummarySiteModel.objects.filter(
        management_regimes__0__name=original_management_name
    ).exists()

    management1.name = "Changing my name"
    management1.save()

    assert (
        SummarySiteModel.objects.filter(
            management_regimes__0__name=original_management_name
        ).exists()
        is False
    )
    assert SummarySiteModel.objects.filter(
        management_regimes__0__name=management1.name
    ).exists()


def test_edit_project_profile(belt_fish_project, project_profile1):
    project_id = project_profile1.project_id
    update_project_summaries(project_id)

    for ssm in SummarySiteModel.objects.all():
        assert len(ssm.project_admins) == 1

    project_profile1.role = ProjectProfile.COLLECTOR
    project_profile1.save()

    for ssm in SummarySiteModel.objects.all():
        assert len(ssm.project_admins) == 0


def test_edit_project(belt_fish_project, project1):
    update_project_summaries(project1.pk)

    new_name = "Change the name"
    project1.name = new_name
    project1.save()

    for ssm in SummarySiteModel.objects.all():
        assert ssm.project_name == new_name
