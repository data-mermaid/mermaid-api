import os
import uuid
from pathlib import Path
from tempfile import NamedTemporaryFile
from zipfile import ZIP_DEFLATED, ZipFile

from django.conf import settings

from ..mocks import MockRequest
from ..models import PROTOCOL_MAP
from ..reports import attributes_report
from ..reports.summary_report import (
    create_protocol_report,
    check_su_method_policy_level,
)
from . import delete_file, s3
from .q import submit_job
from .email import send_mermaid_email


SAMPLE_UNIT_METHOD_REPORT_TYPE = "summary_sample_unit_method"
REPORT_TYPES = [
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

    data_policy_level = check_su_method_policy_level(
        request,
        protocol,
        project_ids
    )

    with NamedTemporaryFile(delete=False) as f:
        output_path = Path(f.name)
        wb = create_protocol_report(request, project_ids, protocol, data_policy_level, output_path)
        try:
            wb.save(output_path)
        except Exception as e:
            print(f"Error saving workbook: {e}")
            return None

        if send_email:
            renamed_xlsx_file = None
            zip_file_path = None
            try:
                file_name = f"{protocol}_summary_{uuid.uuid4()}"
                s3_zip_file_key = f"{settings.ENVIRONMENT}/reports/{file_name}.zip"

                # Rename temporary file
                renamed_xlsx_file = output_path.with_name(f"{file_name}.xlsx")
                os.rename(output_path, renamed_xlsx_file)
                
                zip_file_path = output_path.with_name(f"{file_name}.zip")
                with ZipFile(zip_file_path, "w", compression=ZIP_DEFLATED) as z:
                    z.write(renamed_xlsx_file, arcname=f"{file_name}.xlsx")

                s3.upload_file(settings.AWS_DATA_BUCKET, zip_file_path, s3_zip_file_key)
                file_url = s3.get_presigned_url(settings.AWS_DATA_BUCKET, s3_zip_file_key)
                to = [request.user.profile.email]
                template = "emails/protocol_report.html"
                context = {
                    "protocol": PROTOCOL_MAP.get(protocol) or "",
                    "file_url": file_url
                }
                send_mermaid_email(
                    "Summary Sample Unit Method Report",
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
