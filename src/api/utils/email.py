import datetime

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from maintenance_mode.core import get_maintenance_mode
from pathlib import Path

from ..models.mermaid import ProjectProfile
from .q import submit_job


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


def _mermaid_email(subject, template, to, context=None, from_email=None, reply_to=None):
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

    msg.send()


def _to_in_dev_emails(to):
    to_emails = []
    for to_email in to:
        dev_email_match = [
            email for email in settings.DEV_EMAILS if to_email.endswith(email)
        ]
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
    if get_maintenance_mode() is False:
        to_emails = to
        if settings.ENVIRONMENT not in ("prod",):
            to_emails = _to_in_dev_emails(to)

        if to_emails:
            submit_job(
                delay=0,
                callable=_mermaid_email,
                subject=subject,
                template=template,
                to=to_emails,
                context=context,
                from_email=from_email,
                reply_to=reply_to,
            )
    else:
        text_content, html_content = _get_mermaid_email_content(template, context)
        print(text_content)


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
