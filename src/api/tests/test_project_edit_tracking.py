from api.models import FISHBELT_PROTOCOL, ProjectProfile, SummarySampleEventModel
from api.resources.sampleunitmethods.beltfishmethod import BeltFishMethodSerializer
from api.submission.utils import write_collect_record
from api.utils import Testing
from api.utils.sample_unit_methods import edit_transect_method
from api.utils.summary_cache import update_summary_cache


def test_project_edit_tracking(valid_collect_record, profile1_request):
    with Testing():
        project_id = valid_collect_record.project_id
        write_collect_record(valid_collect_record, profile1_request)

        summary_ses = SummarySampleEventModel.objects.filter(project_id=project_id)
        assert summary_ses.count() == 1

        sse = summary_ses.first()
        beltfish_su_count = sse.protocols["beltfish"]["sample_unit_count"]
        assert beltfish_su_count == 1


def test_edit_transect_method(belt_fish_project, belt_fish1, profile1, profile1_request):
    with Testing():
        project_id = belt_fish1.transect.sample_event.site.project_id

        update_summary_cache(project_id)
        summary_se_count = SummarySampleEventModel.objects.filter(project_id=project_id).count()

        assert summary_se_count == 2

        edit_transect_method(
            BeltFishMethodSerializer,
            profile1,
            profile1_request,
            belt_fish1.pk,
            FISHBELT_PROTOCOL,
        )

        summary_se_count = SummarySampleEventModel.objects.filter(project_id=project_id).count()

        assert summary_se_count == 1


def test_edit_site(belt_fish_project, site1):
    with Testing():
        project_id = site1.project_id
        update_summary_cache(project_id)

        original_site_name = site1.name

        assert SummarySampleEventModel.objects.filter(site_name=original_site_name).exists()

        site1.name = "Changing my name"
        site1.save()

        assert (
            SummarySampleEventModel.objects.filter(site_name=original_site_name).exists() is False
        )
        assert SummarySampleEventModel.objects.filter(site_name=site1.name).exists()


def test_edit_management(belt_fish_project, management1):
    with Testing():
        project_id = management1.project_id
        update_summary_cache(project_id)

        original_management_name = management1.name

        assert SummarySampleEventModel.objects.filter(
            management_name=original_management_name
        ).exists()

        management1.name = "Changing my name"
        management1.save()

        assert (
            SummarySampleEventModel.objects.filter(
                management_name=original_management_name
            ).exists()
            is False
        )
        assert SummarySampleEventModel.objects.filter(management_name=management1.name).exists()


def test_edit_project_profile(belt_fish_project, project_profile1):
    with Testing():
        project_id = project_profile1.project_id
        update_summary_cache(project_id)

        for ssm in SummarySampleEventModel.objects.all():
            assert len(ssm.project_admins) == 1

        project_profile1.role = ProjectProfile.COLLECTOR
        project_profile1.save()

        for ssm in SummarySampleEventModel.objects.all():
            assert len(ssm.project_admins) == 0


def test_edit_project(belt_fish_project, project1):
    with Testing():
        update_summary_cache(project1.pk)

        new_name = "Change the name"
        project1.name = new_name
        project1.save()

        for ssm in SummarySampleEventModel.objects.all():
            assert ssm.project_name == new_name
