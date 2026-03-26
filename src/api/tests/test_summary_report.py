import pytest

from api.reports.summary_report import _get_project_metadata


@pytest.mark.django_db
def test_get_project_metadata_num_sample_units(project1, benthic_lit1):
    rows = _get_project_metadata([project1.pk], {})
    header = rows[0]
    data = rows[1]

    idx = header.index("Number of Sample Units")
    assert data[idx] == 1
