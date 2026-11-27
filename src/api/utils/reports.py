import shutil
from pathlib import Path
from tempfile import NamedTemporaryFile, mkdtemp

from django.conf import settings

from ..mocks import MockRequest
from ..models import SummaryCacheQueue
from ..reports import attributes_report
from ..reports.summary_report import create_protocol_report
from . import create_iso_date_string, s3
from .email import email_report
from .q import submit_job
from .summary_cache import SUMMARY_REPORT_VISIBILITY_TIMEOUT, wait_for_summary_cache

SAMPLE_UNIT_METHOD_REPORT_TYPE = "summary_sample_unit_method"
GFCR_REPORT_TYPE = "gfcr"
REPORT_TYPES = [
    (GFCR_REPORT_TYPE, "GFCR Report"),
    (SAMPLE_UNIT_METHOD_REPORT_TYPE, "Summary Sample Unit Method Report"),
]


def update_attributes_report(local_output_dir=None):
    # Skip in tests: submit_job runs inline under settings.TESTING, so every
    # approved-attribute save would otherwise build + upload the report to S3
    # (None bucket in CI -> TypeError; real bucket locally -> pollutes prod).
    if settings.TESTING and local_output_dir is None:
        return

    canonical_filename = "mermaid_attributes.xlsx"
    dated_filename = f"mermaid_attributes_{create_iso_date_string()}.xlsx"

    with NamedTemporaryFile() as tmp:
        attributes_report.write_attribute_reference(tmp.name)
        tmp.flush()
        if local_output_dir is not None:
            out = Path(local_output_dir)
            shutil.copy(tmp.name, out / canonical_filename)
            shutil.copy(tmp.name, out / dated_filename)
            print(f"Saved {out / canonical_filename}")
            print(f"Saved {out / dated_filename}")
        else:
            s3.upload_file(settings.PUBLIC_BUCKET, tmp.name, canonical_filename)
            s3.copy_object_server_side(
                settings.PUBLIC_BUCKET, canonical_filename, settings.PUBLIC_BUCKET, dated_filename
            )


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
        wait_for_cache=True,
        visibility_timeout=SUMMARY_REPORT_VISIBILITY_TIMEOUT,
    )


def create_sample_unit_method_summary_report(
    project_ids,
    protocol,
    request=None,
    send_email=None,
    wait_for_cache=False,
):
    request = request or MockRequest()

    if send_email and (not hasattr(request, "user") or not hasattr(request.user, "profile")):
        print("No user profile found. Skipping creating report.")
        return None

    if isinstance(project_ids, list) is False:
        project_ids = [project_ids]

    data_may_be_stale = wait_for_summary_cache(project_ids) if wait_for_cache else False

    # Narrow the TOCTOU window: re-check for submissions that raced in after the
    # wait cleared but before we generate.
    if wait_for_cache and not data_may_be_stale:
        if SummaryCacheQueue.objects.filter(project_id__in=project_ids).exists():
            data_may_be_stale = True

    wb = create_protocol_report(request, project_ids, protocol)

    # Unique directory per report: the file name is the same for every report of
    # this protocol created on a given day, and callers use it for the download name.
    output_dir = Path(mkdtemp())
    output_path = output_dir / f"{create_iso_date_string()}_{protocol}.xlsx"
    try:
        wb.save(output_path)
    except Exception as e:
        print(f"Error saving workbook: {e}")
        shutil.rmtree(output_dir, ignore_errors=True)
        return None

    if not send_email:
        # The caller owns output_path.parent and must remove it when done.
        return output_path

    try:
        email_report(
            request.user.profile.email,
            output_path,
            protocol,
            data_may_be_stale=data_may_be_stale,
        )
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)
