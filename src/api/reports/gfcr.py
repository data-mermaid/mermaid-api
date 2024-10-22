import uuid
from functools import lru_cache
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import List
from zipfile import ZIP_DEFLATED, ZipFile

from django.conf import settings

from ..mocks import MockRequest
from ..models import GFCRFinanceSolution, GFCRIndicatorSet
from ..utils import castutils, delete_file, s3
from ..utils.email import send_mermaid_email
from ..utils.q import submit_job
from ..utils.timer import timing
from . import xl


@lru_cache
def common_columns(indicator_set):
    return [
        indicator_set.project.name,
        indicator_set.title,
        indicator_set.report_date,
        indicator_set.indicator_set_type,
    ]


def f1_data(indicator_sets):
    for indicator_set in indicator_sets:
        yield common_columns(indicator_set) + [
            indicator_set._meta.get_field("f1_1").verbose_name,
            indicator_set.f1_1,
        ]


def _get_indicator_set_field_data(
    indicator_set, field_label, field_name, additional_column_fields: List[str] = None
):
    if not additional_column_fields:
        additional_column_fields = []

    return (
        common_columns(indicator_set)
        + [
            f"{field_label} {indicator_set._meta.get_field(field_name).verbose_name}",
            getattr(indicator_set, field_name),
        ]
        + [getattr(indicator_set, f) for f in additional_column_fields]
    )


def _get_indicator_sheet_data(indicator_sets, fields, additional_column_fields=None):
    for indicator_set in indicator_sets:
        for field_label, field_name in fields:
            if hasattr(indicator_set, field_name) and getattr(indicator_set, field_name):
                yield _get_indicator_set_field_data(
                    indicator_set,
                    field_label,
                    field_name,
                    additional_column_fields=additional_column_fields,
                )


def f2_data(indicator_sets):
    fields = (
        ("F2.1a", "f2_1a"),
        ("F2.1b", "f2_1b"),
        ("F2.2a", "f2_2a"),
        ("F2.2b", "f2_2b"),
        ("F2.3a", "f2_3a"),
        ("F2.3b", "f2_3b"),
        ("F2.4", "f2_4"),
        ("F2 Optional:", "f2_opt1"),
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
        indicator_sets, fields, additional_column_fields=["f4_start_date", "f4_end_date"]
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


@lru_cache
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
                        rev.annual_revenue,
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
    sheet_data["Revenue"] = revenue_data(indicator_sets)

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

    with NamedTemporaryFile(delete=False) as f:
        output_path = Path(f.name)
        try:
            wb.save(output_path)
        except Exception as e:
            print(f"Error saving workbook: {e}")
            return None

        if send_email:
            renamed_xlsx_file = None
            zip_file_path = None
            try:
                file_name = f"gfcr_{uuid.uuid4()}"
                s3_zip_file_key = f"{settings.ENVIRONMENT}/reports/{file_name}.zip"

                # Rename temporary file
                renamed_xlsx_file = output_path.with_name(f"{file_name}.xlsx")
                output_path.rename(renamed_xlsx_file)

                zip_file_path = output_path.with_name(f"{file_name}.zip")
                with ZipFile(zip_file_path, "w", compression=ZIP_DEFLATED) as z:
                    z.write(renamed_xlsx_file, arcname=f"{file_name}.xlsx")

                s3.upload_file(settings.AWS_DATA_BUCKET, zip_file_path, s3_zip_file_key)
                file_url = s3.get_presigned_url(settings.AWS_DATA_BUCKET, s3_zip_file_key)
                to = [request.user.profile.email]
                template = "emails/gfcr_report.html"
                context = {"file_url": file_url}
                send_mermaid_email(
                    "GFCR Report",
                    template,
                    to,
                    context=context,
                )
            except Exception as e:
                print(f"Error sending email or uploading to S3: {e}")
                return None
            finally:
                delete_file(renamed_xlsx_file)
                delete_file(zip_file_path)

        return output_path


def create_report_background(project_ids, request=None, send_email=None):
    req = MockRequest.load_request(request)
    submit_job(
        0,
        create_report,
        project_ids,
        request=req,
        send_email=send_email,
    )
