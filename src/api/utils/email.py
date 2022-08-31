import datetime

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from pathlib import Path

from ..models.mermaid import ProjectProfile
from .q import submit_job


def _get_message_parts(
    subject, template, to, context=None, from_email=None, reply_to=None
):
    _subject = f"[MERMAID] {subject}"
    path = Path(template).parent / Path(template).stem
    template_dir = settings.TEMPLATES[0]["DIRS"][0]
    template_html = f"{path}.html"
    template_text = f"{path}.txt"

    context = context or {}
    context["timestamp"] = datetime.datetime.utcnow().replace(microsecond=0).isoformat()
    text_content = render_to_string(template_text, context=context)
    from_email = from_email or settings.DEFAULT_FROM_EMAIL
    reply_to = reply_to or [settings.DEFAULT_FROM_EMAIL]

    message_parts = {
        "subject": _subject,
        "text_content": text_content,
        "to": to,
        "context": context,
        "from_email": from_email,
        "reply_to": reply_to,
    }
    if (Path(template_dir) / template_html).is_file():
        html_content = render_to_string(template_html, context=context)
        message_parts["html_content"] = html_content

    return message_parts


def _mermaid_email(subject, template, to, context=None, from_email=None, reply_to=None):
    message_parts = _get_message_parts(
        subject, template, to, context, from_email, reply_to
    )

    msg = EmailMultiAlternatives(
        message_parts["subject"],
        message_parts["text_content"],
        to=message_parts["to"],
        from_email=message_parts["from_email"],
        reply_to=message_parts["reply_to"],
    )
    if "html_content" in message_parts:
        msg.attach_alternative(message_parts["html_content"], "text/html")

    msg.send()


def mermaid_email(subject, template, to, context=None, from_email=None, reply_to=None):
    if settings.ENVIRONMENT == "prod":
        submit_job(
            delay=0,
            callable=_mermaid_email,
            subject=subject,
            template=template,
            to=to,
            context=context,
            from_email=from_email,
            reply_to=reply_to,
        )
    else:
        message_parts = _get_message_parts(
            subject, template, to, context, from_email, reply_to
        )
        print(message_parts["text_content"])


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
