import datetime
import os

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

from ..models.mermaid import ProjectProfile
from .q import submit_job


def _mermaid_email(
    subject, template, to, context=None, from_email=None, reply_to=None
):
    _subject = f"[MERMAID] {subject}"
    path, _ = os.path.splitext(template)
    template_html = f"{path}.html"
    template_text = f"{path}.txt"

    context = context or {}
    context["timestamp"] = datetime.datetime.utcnow().replace(microsecond=0).isoformat()
    text_content = render_to_string(template_text, context=context)
    html_content = render_to_string(template_html, context=context)
    from_email = from_email or settings.DEFAULT_FROM_EMAIL
    reply_to = reply_to or [settings.DEFAULT_FROM_EMAIL]

    if settings.ENVIRONMENT == "prod":
        msg = EmailMultiAlternatives(
            _subject, text_content, to=to, from_email=from_email, reply_to=reply_to
        )
        msg.attach_alternative(html_content, "text/html")
        msg.send()
    else:
        print(text_content)


def mermaid_email(
    subject, template, to, context=None, from_email=None, reply_to=None
):
    submit_job(
        delay=0,
        callable=_mermaid_email,
        subject=subject,
        template=template,
        to=to,
        context=context,
        from_email=from_email,
        reply_to=reply_to
    )


def email_project_admins(project, subject, template, context, from_email=None):
    project_admins = ProjectProfile.objects.filter(
        project_id=project, role=ProjectProfile.ADMIN
    ).select_related("profile")
    project_admin_emails = [p.profile.email for p in project_admins]
    from_email = from_email or settings.DEFAULT_FROM_EMAIL

    if project_admins.count() > 0:
        mermaid_email(
            subject,
            template,
            project_admin_emails,
            context=context,
            from_email=from_email,
            reply_to=project_admin_emails
        )


# for hooking up to https://api.datamermaid.org/contact_project?project_id=2c56b92b-ba1c-491f-8b62-23b1dc728890
def contact_project_admins(project, subject, body, from_email):
    # lots of checking/validation/antispam here
    # email_project_admins(project, subject, body, from_email=from_email)
    pass
