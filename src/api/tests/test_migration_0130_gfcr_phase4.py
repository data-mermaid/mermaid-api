import importlib
from datetime import date

import pytest
from django.db import connection

from api.models import (
    GFCRFinanceSolution,
    GFCRIndicatorSet,
    GFCRInvestmentSource,
    GFCRRevenue,
)

_migration_module = importlib.import_module("api.migrations.0130_gfcr_phase4")
assert_phase4_preconditions = _migration_module.assert_phase4_preconditions


class _FakeSchemaEditor:
    def __init__(self, db_connection):
        self.connection = db_connection


def _run_precondition_check():
    assert_phase4_preconditions(None, _FakeSchemaEditor(connection))


@pytest.fixture
def clean_indicator_set(project1):
    return GFCRIndicatorSet.objects.create(
        project=project1,
        title="Baseline",
        report_date="2024-02-10",
        indicator_set_type="report",
        f4_start_date=date(1970, 1, 1),
        f4_end_date=date(2024, 4, 19),
    )


@pytest.fixture
def clean_finance_solution(clean_indicator_set):
    return GFCRFinanceSolution.objects.create(
        indicator_set=clean_indicator_set,
        name="My FS",
        fs_type="business",
        sector="ce_waste_management",
    )


def test_phase4_preconditions_pass_on_clean_data(db_setup, clean_finance_solution):
    GFCRInvestmentSource.objects.create(
        finance_solution=clean_finance_solution,
        investment_source="gfcr",
        investment_type="grant",
        investment_amount=100,
    )
    GFCRRevenue.objects.create(
        finance_solution=clean_finance_solution,
        revenue_type="ecotourism",
        revenue_amount=100,
    )

    _run_precondition_check()


def test_phase4_preconditions_rejects_invalid_fs_type(db_setup, clean_finance_solution):
    GFCRFinanceSolution.objects.filter(pk=clean_finance_solution.pk).update(fs_type="fm_other")

    with pytest.raises(RuntimeError, match="invalid fs_type"):
        _run_precondition_check()


def test_phase4_preconditions_rejects_deprecated_sector(db_setup, clean_finance_solution):
    GFCRFinanceSolution.objects.filter(pk=clean_finance_solution.pk).update(
        sector="fm_mpa_user_fee"
    )

    with pytest.raises(RuntimeError, match="deprecated fm_"):
        _run_precondition_check()


def test_phase4_preconditions_rejects_deprecated_sfm(db_setup, clean_finance_solution):
    GFCRFinanceSolution.objects.filter(pk=clean_finance_solution.pk).update(
        sustainable_finance_mechanisms=["revolving_finance_facility"]
    )

    with pytest.raises(RuntimeError, match="deprecated SFM"):
        _run_precondition_check()


def test_phase4_preconditions_rejects_public_budget_investment_type(
    db_setup, clean_finance_solution
):
    GFCRInvestmentSource.objects.create(
        finance_solution=clean_finance_solution,
        investment_source="public",
        investment_type="public_budget",
        investment_amount=100,
    )

    with pytest.raises(RuntimeError, match="public_budget"):
        _run_precondition_check()


def test_phase4_preconditions_rejects_invalid_indicator_set_title(db_setup, clean_indicator_set):
    GFCRIndicatorSet.objects.filter(pk=clean_indicator_set.pk).update(title="Not a real title")

    with pytest.raises(RuntimeError, match="valid canonical title"):
        _run_precondition_check()


def test_phase4_preconditions_rejects_target_title_on_report_type(db_setup, clean_indicator_set):
    GFCRIndicatorSet.objects.filter(pk=clean_indicator_set.pk).update(title="Phase 1 target")

    with pytest.raises(RuntimeError, match="used with 'report' type"):
        _run_precondition_check()


def test_phase4_preconditions_rejects_revenue_on_pcf_finance_solution(
    db_setup, clean_finance_solution
):
    GFCRFinanceSolution.objects.filter(pk=clean_finance_solution.pk).update(
        fs_type="programmatic_co_financing"
    )
    GFCRRevenue.objects.create(
        finance_solution=clean_finance_solution,
        revenue_type="ecotourism",
        revenue_amount=50,
    )

    with pytest.raises(RuntimeError, match="linked to PCF finance solutions"):
        _run_precondition_check()
