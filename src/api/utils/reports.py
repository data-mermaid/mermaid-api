from pathlib import Path
from tempfile import NamedTemporaryFile

from django.conf import settings

from ..mocks import MockRequest
from ..reports import attributes_report
from ..reports.summary_report import (
    create_protocol_report,
    group_projects_by_policy_level,
)
from . import delete_file, s3, zip_file
from .email import email_report
from .q import submit_job

SAMPLE_UNIT_METHOD_REPORT_TYPE = "summary_sample_unit_method"
GFCR_REPORT_TYPE = "gfcr"
REPORT_TYPES = [
    (GFCR_REPORT_TYPE, "GFCR Report"),
    (SAMPLE_UNIT_METHOD_REPORT_TYPE, "Summary Sample Unit Method Report"),
]


def update_attributes_report():
    with NamedTemporaryFile() as tmp:
        attributes_report.write_attribute_reference(tmp.name)
        s3.upload_file(settings.PUBLIC_BUCKET, tmp.name, "mermaid_attributes.xlsx")


def create_sample_unit_method_summary_report_background(
    project_ids,
    protocol,
    request=None,
    send_email=None,
):
    req = MockRequest.load_request(request)
    submit_job(
        0,
        True,
        create_sample_unit_method_summary_report,
        project_ids,
        protocol,
        request=req,
        send_email=send_email,
    )


def create_sample_unit_method_summary_report(
    project_ids,
    protocol,
    request=None,
    send_email=None,
):
    request = request or MockRequest()

    if send_email and (not hasattr(request, "user") or not hasattr(request.user, "profile")):
        print("No user profile found. Skipping creating report.")
        return None

    if isinstance(project_ids, list) is False:
        project_ids = [project_ids]

    project_groups = group_projects_by_policy_level(request, protocol, project_ids)

    output_file_paths = []
    for data_policy_level, project_ids in project_groups.items():
        with NamedTemporaryFile(prefix=f"{data_policy_level}_", suffix=".xlsx", delete=False) as f:
            output_path = Path(f.name)
            wb = create_protocol_report(request, project_ids, protocol, data_policy_level)
            try:
                wb.save(output_path)
            except Exception as e:
                print(f"Error saving workbook: {e}")
                return None
            output_file_paths.append(output_path)

    zip_output_path = zip_file(output_file_paths, protocol)
    delete_file(output_file_paths)

    if send_email:
        email_report(request.user.profile.email, zip_output_path, protocol)
        delete_file(zip_output_path)
    else:
        return zip_output_path
