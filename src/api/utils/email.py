import datetime
import logging
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from maintenance_mode.core import get_maintenance_mode

from ..models import PROTOCOL_MAP
from ..models.mermaid import ProjectProfile
from ..utils import create_iso_date_string
from . import delete_file, s3
from .q import submit_job

logger = logging.getLogger(__name__)


def _get_mermaid_email_content(template, context):
    path = Path(template).parent / Path(template).stem
    template_dir = settings.TEMPLATES[0]["DIRS"][0]
    template_html = f"{path}.html"
    template_text = f"{path}.txt"
    context = context or {}
    context["timestamp"] = datetime.datetime.utcnow().replace(microsecond=0).isoformat()

    text_content = render_to_string(template_text, context=context)
    html_content = None
    if (Path(template_dir) / template_html).is_file():
        html_content = render_to_string(template_html, context=context)
    return text_content, html_content


def send_mermaid_email(subject, template, to, context=None, from_email=None, reply_to=None):
    _subject = f"[MERMAID] {subject}"
    text_content, html_content = _get_mermaid_email_content(template, context)
    from_email = from_email or settings.DEFAULT_FROM_EMAIL
    reply_to = reply_to or [settings.DEFAULT_FROM_EMAIL]
    if not isinstance(reply_to, (list, tuple)):
        reply_to = [reply_to]

    msg = EmailMultiAlternatives(
        _subject, text_content, to=to, from_email=from_email, reply_to=reply_to
    )
    if html_content:
        msg.attach_alternative(html_content, "text/html")

    if get_maintenance_mode() is False:
        msg.send()
    else:
        print(text_content)


def _to_in_dev_emails(to):
    to_emails = []
    for to_email in to:
        dev_email_match = [email for email in settings.DEV_EMAILS if to_email.endswith(email)]
        if dev_email_match:
            to_emails.append(to_email)
    return to_emails


def mermaid_email(subject, template, to, context=None, from_email=None, reply_to=None):
    # if maintenance mode is on: console
    # if local and not dev email and pytest: console
    # if local and not dev email and not pytest: console
    # if local and dev email and pytest: submit_job (locmem)
    # if local and dev email and not pytest: console
    # if dev and not dev email: console
    # if dev and dev email: submit_job
    # if prod: submit_job
    to_emails = to
    if settings.ENVIRONMENT != "prod":
        to_emails = _to_in_dev_emails(to)

    if to_emails:
        submit_job(
            delay=0,
            loggable=False,
            callable=send_mermaid_email,
            subject=subject,
            template=template,
            to=to_emails,
            context=context,
            from_email=from_email,
            reply_to=reply_to,
        )


def email_mermaid_admins(**kwargs):
    template = "emails/contact_mermaid_admins.html"
    from_email = kwargs["from_email"]
    context = {
        "message": kwargs["message"],
        "name": kwargs["name"],
        "from_email": from_email,
    }

    mermaid_email(
        kwargs["subject"],
        template,
        [settings.SUPERUSER[1]],
        context=context,
        from_email=settings.WEBCONTACT_EMAIL,
        reply_to=from_email,
    )


def email_project_admins(**kwargs):
    template = "emails/contact_project_admins.html"
    from_email = kwargs["from_email"]
    project = kwargs["project"]
    context = {
        "message": kwargs["message"],
        "name": kwargs["name"],
        "from_email": from_email,
        "project": project,
    }
    project_admins = ProjectProfile.objects.filter(
        project_id=project, role=ProjectProfile.ADMIN
    ).select_related("profile")
    project_admin_emails = [p.profile.email for p in project_admins]

    if project_admins.count() > 0:
        mermaid_email(
            kwargs["subject"],
            template,
            project_admin_emails,
            context=context,
            from_email=settings.WEBCONTACT_EMAIL,
            reply_to=from_email,
        )


def email_report(to_email, local_file_path, protocol, data_policy_level):
    if not to_email or "@" not in to_email:
        raise ValueError("Invalid email address")
    if not local_file_path or not Path(local_file_path).is_file():
        raise ValueError("Invalid or missing file path")
    if not protocol:
        raise ValueError("Report title is required")

    try:
        zip_file_path = None
        local_file_path = Path(local_file_path)
        data_policy = f"_{data_policy_level}" if data_policy_level is not None else ""
        file_name = f"{create_iso_date_string()}_{protocol}{data_policy}.xlsx"
        s3_zip_file_key = f"{settings.ENVIRONMENT}/reports/{file_name}.zip"

        zip_file_path = local_file_path.with_name(f"{file_name}.zip")
        with ZipFile(zip_file_path, "w", compression=ZIP_DEFLATED) as z:
            z.write(local_file_path, arcname=file_name)

        s3.upload_file(settings.AWS_DATA_BUCKET, zip_file_path, s3_zip_file_key)
    except Exception:
        logger.exception("Uploading report S3")
        return False
    finally:
        delete_file(zip_file_path)

    try:
        file_url = s3.get_presigned_url(settings.AWS_DATA_BUCKET, s3_zip_file_key)
        to = [to_email]
        template = "emails/report.html"
        report_title = PROTOCOL_MAP.get(protocol) or ""
        context = {"file_url": file_url, "title": report_title}
        send_mermaid_email(
            f"{report_title} Report",
            template,
            to,
            context=context,
        )
        return True
    except Exception:
        logger.exception("Emailing report")
        return False
