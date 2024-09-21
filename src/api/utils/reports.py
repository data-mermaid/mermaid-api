import uuid
from tempfile import NamedTemporaryFile

from django.conf import settings

from ..mocks import MockRequest
from ..models import (
    BENTHICLIT_PROTOCOL,
    BENTHICPIT_PROTOCOL,
    BENTHICPQT_PROTOCOL,
    BLEACHINGQC_PROTOCOL,
    FISHBELT_PROTOCOL,
    HABITATCOMPLEXITY_PROTOCOL,
)
from ..reports import attributes_report
from ..reports.summary_report import (
    create_belt_fish_report,
    create_benthic_lit_report,
    create_benthic_pit_report,
    create_benthic_pqt_report,
    create_bleaching_qc_report,
    create_habitat_complexity_report,
    check_su_method_policy_level,
)
from . import s3
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

    _data_policy_level = check_su_method_policy_level(
        request,
        protocol,
        project_ids
    )
    if protocol == BENTHICLIT_PROTOCOL:
        wb = create_benthic_lit_report(request, project_ids, _data_policy_level)
    elif protocol == BENTHICPIT_PROTOCOL:
        wb = create_benthic_pit_report(request, project_ids, _data_policy_level)
    elif protocol == FISHBELT_PROTOCOL:
        wb = create_belt_fish_report(request, project_ids, _data_policy_level)
    elif protocol == HABITATCOMPLEXITY_PROTOCOL:
        wb = create_habitat_complexity_report(request, project_ids, _data_policy_level)
    elif protocol == BLEACHINGQC_PROTOCOL:
        wb = create_bleaching_qc_report(request, project_ids, _data_policy_level)
    elif protocol == BENTHICPQT_PROTOCOL:
        wb = create_benthic_pqt_report(request, project_ids, _data_policy_level)
    else:
        raise ValueError(f"Unknown protocol [{protocol}]")
    
    with NamedTemporaryFile(delete=False) as f:
        output_path = f.name
    
        try:
            wb.save(output_path)
        except Exception as e:
            print(f"Error saving workbook: {e}")
            return None

    if send_email:
        try:
            file_name = f"{settings.ENVIRONMENT}/reports/summary_sample_method_{uuid.uuid4()}.xlsx"
            s3.upload_file(settings.AWS_DATA_BUCKET, output_path, file_name)
            file_url = s3.get_presigned_url(settings.AWS_DATA_BUCKET, file_name)
            to = [request.user.profile.email]
            template = "emails/summary_sample_event.html"
            context = {
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

    return output_path
