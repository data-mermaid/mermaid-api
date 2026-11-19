from datetime import date

import pytest

from api.models import (
    GFCRFinanceSolution,
    GFCRIndicatorSet,
    GFCRInvestmentSource,
    GFCRRevenue,
)
from api.reports.gfcr import get_indicator_sets, report_data

INDICATOR_SETS_PER_PROJECT = 3
FINANCE_SOLUTIONS_PER_SET = 2
INVESTMENTS_PER_FS = 3
REVENUES_PER_FS = 2

# 1 indicator sets (+ project), 3 prefetches (finance solutions, investment
# sources, revenues), plus 2 citation queries per project (profiles, latest
# sample event). Does not grow with the number of indicator sets, finance
# solutions, investment sources or revenues.
MAX_REPORT_QUERIES = 10


@pytest.fixture
def gfcr_report_projects(project1, project2):
    for project in (project1, project2):
        project.includes_gfcr = True
        project.save()
        for i in range(INDICATOR_SETS_PER_PROJECT):
            indicator_set = GFCRIndicatorSet.objects.create(
                project=project,
                title="Baseline",
                report_date=date(2024, 1, i + 1),
                indicator_set_type="report",
                f4_start_date=date(1970, 1, 1),
                f4_end_date=date(2024, 4, 19),
            )
            for j in range(FINANCE_SOLUTIONS_PER_SET):
                fs = GFCRFinanceSolution.objects.create(
                    indicator_set=indicator_set,
                    name=f"{project.name} IS{i} FS{j}",
                    fs_type="business",
                    sector="ce_waste_management",
                )
                for k in range(INVESTMENTS_PER_FS):
                    GFCRInvestmentSource.objects.create(
                        finance_solution=fs,
                        investment_source="public",
                        investment_type="grant",
                        investment_amount=1000 * (k + 1),
                        notes=f"{fs.name} investment {k}",
                    )
                for k in range(REVENUES_PER_FS):
                    GFCRRevenue.objects.create(
                        finance_solution=fs,
                        revenue_type="ecotourism",
                        revenue_amount=500 * (k + 1),
                        notes=f"{fs.name} revenue {k}",
                    )
    return [project1.pk, project2.pk]


def _consume(sheet_data):
    return {sheet_name: list(rows) for sheet_name, rows in sheet_data.items()}


def _sorted(rows):
    return sorted(rows, key=str)


def test_report_data_query_count_is_constant(gfcr_report_projects, django_assert_max_num_queries):
    project_ids = gfcr_report_projects

    # Baseline: rows built from a plain, unprefetched queryset.
    expected = _consume(report_data(GFCRIndicatorSet.objects.filter(project_id__in=project_ids)))

    with django_assert_max_num_queries(MAX_REPORT_QUERIES):
        actual = _consume(report_data(get_indicator_sets(project_ids)))

    num_fs = 2 * INDICATOR_SETS_PER_PROJECT * FINANCE_SOLUTIONS_PER_SET
    assert len(actual["Investments"]) == num_fs * INVESTMENTS_PER_FS
    assert len(actual["Revenues"]) == num_fs * REVENUES_PER_FS

    assert _sorted(actual["Investments"]) == _sorted(expected["Investments"])
    assert _sorted(actual["Revenues"]) == _sorted(expected["Revenues"])
    assert _sorted(actual["FacilitiesSolutions"]) == _sorted(expected["FacilitiesSolutions"])
