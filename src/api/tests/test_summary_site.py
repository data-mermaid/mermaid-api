from django.db import connection

from api.models import SummarySiteViewModel, Site


def test_depth_avg(
    belt_transect_width_2m,
    belt_transect_width_condition1,
    fish_size_bin_1,
    obs_belt_fish1_1,
    obs_belt_fish1_2,
    obs_belt_fish1_3,
    observer_belt_fish1,
    obs_belt_fish3_1,
    obs_belt_fish3_2,
    obs_belt_fish3_3,
    observer_belt_fish3,
    obs_benthic_pit1_1,
    obs_benthic_pit1_2,
    obs_benthic_pit1_3,
    obs_benthic_pit1_4,
    observer_benthic_pit1,
    project_profile1,
):
    with connection.cursor() as cursor:
        cursor.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY vw_summary_site")

    assert Site.objects.all().count() == 1
    assert SummarySiteViewModel.objects.all().count() == 1
    assert SummarySiteViewModel.objects.all()[0].depth_avg_max == 6.5
