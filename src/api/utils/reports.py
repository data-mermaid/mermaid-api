from pathlib import Path
from tempfile import NamedTemporaryFile

from django.conf import settings

from ..mocks import MockRequest
from ..models import PROTOCOL_MAP
from ..reports import attributes_report
from ..reports.summary_report import check_su_method_policy_level, create_protocol_report
from . import delete_file, s3
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

    data_policy_level = check_su_method_policy_level(request, protocol, project_ids)

    with NamedTemporaryFile(delete=False, prefix=f"{protocol}_", suffix=".xlsx") as f:
        output_path = Path(f.name)
        wb = create_protocol_report(request, project_ids, protocol, data_policy_level)
        try:
            wb.save(output_path)
        except Exception as e:
            print(f"Error saving workbook: {e}")
            return None

        if send_email:
            email_report(request.user.profile.email, output_path, PROTOCOL_MAP.get(protocol) or "")
            delete_file(output_path)
        else:
            return output_path
