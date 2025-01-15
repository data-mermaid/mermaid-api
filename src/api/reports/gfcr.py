import logging
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import List

from ..mocks import MockRequest
from ..models import GFCRFinanceSolution, GFCRIndicatorSet
from ..utils import castutils, delete_file
from ..utils.email import email_report
from ..utils.q import submit_job
from ..utils.timer import timing
from . import xl

logger = logging.getLogger(__name__)


def common_columns(indicator_set):
    return [
        indicator_set.project.name,
        indicator_set.title,
        indicator_set.report_date,
        indicator_set.get_indicator_set_type_display(),
    ]


def _get_indicator_set_field_data(
    indicator_set, field_label, field_name, additional_common_fields: List[str] = None
):
    if not additional_common_fields:
        additional_common_fields = []

    return (
        common_columns(indicator_set)
        + [getattr(indicator_set, f) for f in additional_common_fields]
        + [
            f"{field_label} {indicator_set._meta.get_field(field_name).verbose_name}",
            getattr(indicator_set, field_name),
        ]
    )


def _get_indicator_sheet_data(indicator_sets, fields, additional_common_fields=None):
    for indicator_set in indicator_sets:
        for field_label, field_name in fields:
            if hasattr(indicator_set, field_name):
                yield _get_indicator_set_field_data(
                    indicator_set,
                    field_label,
                    field_name,
                    additional_common_fields=additional_common_fields,
                )


def f1_data(indicator_sets):
    for indicator_set in indicator_sets:
        if hasattr(indicator_set, "f1_1"):
            yield common_columns(indicator_set) + [
                indicator_set._meta.get_field("f1_1").verbose_name,
                indicator_set.f1_1,
            ]


def f2_data(indicator_sets):
    fields = (
        ("F2.1a", "f2_1a"),
        ("F2.1b", "f2_1b"),
        ("F2.2a", "f2_2a"),
        ("F2.2b", "f2_2b"),
        ("F2.3a", "f2_3a"),
        ("F2.3b", "f2_3b"),
        ("F2.4", "f2_4"),
        ("F2.5:", "f2_5"),
    )
    return _get_indicator_sheet_data(indicator_sets, fields)


def f3_data(indicator_sets):
    fields = (
        ("F3.1", "f3_1"),
        ("F3.2", "f3_2"),
        ("F3.3", "f3_3"),
        ("F3.4", "f3_4"),
        ("F3.5a", "f3_5a"),
        ("F3.5b", "f3_5b"),
        ("F3.5c", "f3_5c"),
        ("F3.5d", "f3_5d"),
        ("F3.6", "f3_6"),
    )
    return _get_indicator_sheet_data(indicator_sets, fields)


def f4_data(indicator_sets):
    fields = (
        ("F4.1", "f4_1"),
        ("F4.2", "f4_2"),
        ("F4.3", "f4_3"),
    )
    return _get_indicator_sheet_data(
        indicator_sets, fields, additional_common_fields=["f4_start_date", "f4_end_date"]
    )


def f5_data(indicator_sets):
    fields = (
        ("F5.1", "f5_1"),
        ("F5.2", "f5_2"),
        ("F5.3", "f5_3"),
        ("F5.4a", "f5_4a"),
        ("F5.4b", "f5_4b"),
        ("F5.4c", "f5_4c"),
        ("F5.4d", "f5_4d"),
        ("F5.5", "f5_5"),
        ("F5.6", "f5_6"),
    )
    return _get_indicator_sheet_data(indicator_sets, fields)


def f6_data(indicator_sets):
    fields = (
        ("F6.1a", "f6_1a"),
        ("F6.1b", "f6_1b"),
        ("F6.1c", "f6_1c"),
        ("F6.1d", "f6_1d"),
        ("F6.2a", "f6_2a"),
        ("F6.2b", "f6_2b"),
        ("F6.2c", "f6_2c"),
        ("F6.2d", "f6_2d"),
    )
    return _get_indicator_sheet_data(indicator_sets, fields)


def f7_data(indicator_sets):
    fields = (
        ("F7.1a", "f7_1a"),
        ("F7.1b", "f7_1b"),
        ("F7.1c", "f7_1c"),
        ("F7.1d", "f7_1d"),
        ("F7.2a", "f7_2a"),
        ("F7.2b", "f7_2b"),
        ("F7.2c", "f7_2c"),
        ("F7.2d", "f7_2d"),
        ("F7.3", "f7_3"),
        ("F7.4", "f7_4"),
    )
    return _get_indicator_sheet_data(indicator_sets, fields)


def common_finance_solutions_columns(finance_solution):
    return [
        finance_solution.name,
        ",".join(finance_solution.get_sustainable_finance_mechanisms_display()),
        finance_solution.get_sector_display(),
    ]


def businesses_finance_solutions_data(indicator_sets):
    for indicator_set in indicator_sets:
        com_cols = common_columns(indicator_set)
        for fs in indicator_set.finance_solutions.all():
            yield (
                com_cols
                + common_finance_solutions_columns(fs)
                + [
                    castutils.to_yesno(fs.used_an_incubator),
                    castutils.to_yesno(fs.used_an_incubator == GFCRFinanceSolution.GFCR_FUNDED),
                    castutils.to_yesno(fs.local_enterprise),
                    castutils.to_yesno(fs.gender_smart),
                ]
            )


def investments_data(indicator_sets):
    for indicator_set in indicator_sets:
        com_cols = common_columns(indicator_set)
        for fs in indicator_set.finance_solutions.all():
            com_fs_cols = common_finance_solutions_columns(fs)
            for investment in fs.investment_sources.all():
                yield (
                    com_cols
                    + com_fs_cols
                    + [
                        investment.get_investment_source_display(),
                        investment.get_investment_type_display(),
                        investment.investment_amount,
                    ]
                )


def revenue_data(indicator_sets):
    for indicator_set in indicator_sets:
        com_cols = common_columns(indicator_set)
        for fs in indicator_set.finance_solutions.all():
            com_fs_cols = common_finance_solutions_columns(fs)
            for rev in fs.revenues.all():
                yield (
                    com_cols
                    + com_fs_cols
                    + [
                        rev.get_revenue_type_display(),
                        castutils.to_yesno(rev.sustainable_revenue_stream),
                        rev.revenue_amount,
                    ]
                )


def report_data(indicator_sets):
    sheet_data = {}
    sheet_data["F1"] = f1_data(indicator_sets)
    sheet_data["F2"] = f2_data(indicator_sets)
    sheet_data["F3"] = f3_data(indicator_sets)
    sheet_data["F4"] = f4_data(indicator_sets)
    sheet_data["F5"] = f5_data(indicator_sets)
    sheet_data["F6"] = f6_data(indicator_sets)
    sheet_data["F7"] = f7_data(indicator_sets)
    sheet_data["BusinessesFinanceSolutions"] = businesses_finance_solutions_data(indicator_sets)
    sheet_data["Investments"] = investments_data(indicator_sets)
    sheet_data["Revenues"] = revenue_data(indicator_sets)

    return sheet_data


@timing
def create_report(project_ids, request=None, send_email=None):
    wb = xl.get_workbook("gfcr")
    request = request or MockRequest()

    if isinstance(project_ids, list) is False:
        project_ids = [project_ids]

    indicator_sets = GFCRIndicatorSet.objects.filter(project_id__in=project_ids)
    sheet_data = report_data(indicator_sets)

    for sheet_name, data in sheet_data.items():
        xl.write_data_to_sheet(wb, sheet_name, data, 2, 1)
        xl.auto_size_columns(wb[sheet_name])

    with NamedTemporaryFile(delete=False, prefix="gfcr_", suffix=".xlsx") as f:
        output_path = Path(f.name)
        try:
            wb.save(output_path)
        except Exception:
            logger.exception("Error saving workbook")
            return None

        if send_email:
            email_report(request.user.profile.email, output_path, "GFCR")
            delete_file(output_path)
        else:
            return output_path


def create_report_background(project_ids, request=None, send_email=None):
    req = MockRequest.load_request(request)
    submit_job(
        0,
        True,
        create_report,
        project_ids,
        request=req,
        send_email=send_email,
    )
