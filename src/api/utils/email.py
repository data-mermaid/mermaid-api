import datetime
import os

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

from ..decorators import run_in_thread
from ..models.mermaid import ProjectProfile


@run_in_thread
def mermaid_email(
    subject, template, to, context=None, from_email=settings.DEFAULT_FROM_EMAIL
):
    _subject = f"[MERMAID] {subject}"
    path, _ = os.path.splitext(template)
    template_html = f"{path}.html"
    template_text = f"{path}.txt"

    context = context or {}
    context["timestamp"] = datetime.datetime.utcnow().replace(microsecond=0).isoformat()
    text_content = render_to_string(template_text, context=context)
    html_content = render_to_string(template_html, context=context)

    if settings.ENVIRONMENT == "prod":
        msg = EmailMultiAlternatives(
            _subject, text_content, from_email, to=[to], reply_to=[from_email]
        )
        msg.attach_alternative(html_content, "text/html")
        msg.send()
    else:
        print(text_content)


def email_project_admins(project, subject, template, context):
    project_admins = ProjectProfile.objects.filter(
        project_id=project, role=ProjectProfile.ADMIN
    ).select_related("profile")

    if project_admins.count() > 0:
        mermaid_email(
            subject,
            template,
            [p.profile.email for p in project_admins],
            context=context,
        )


# for hooking up to https://api.datamermaid.org/contact_project?project_id=2c56b92b-ba1c-491f-8b62-23b1dc728890
def contact_project_admins(project, subject, body, from_email):
    # lots of checking/validation/antispam here
    # email_project_admins(project, subject, body, from_email)
    pass
