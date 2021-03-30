import datetime
from django.conf import settings
from django.core.mail import EmailMessage
from ..models.mermaid import ProjectProfile


def mermaid_email(subject, heading, subheading, body, to, from_email=None):
    SUBJECT_TMPL = u'[MERMAID] {subject}'
    BODY_TMPL = u'''
    <div style="text-align:center; background-color:#666; padding: 20px;">
        <img style="width:auto; display:inline-block;" 
        src="https://datamermaid.org/wp-content/themes/mermaid/img/mermaid_logo.png">
    </div>
    <h2>{heading}</h2>
    <h3>{subheading}</h3>
    <p>{timestamp} UTC</p>
    {body}
    '''

    subject = SUBJECT_TMPL.format(subject=subject)
    timestamp = datetime.datetime.utcnow().replace(microsecond=0).isoformat()
    content = BODY_TMPL.format(heading=heading, subheading=subheading, timestamp=timestamp, body=body)
    from_email = from_email or settings.DEFAULT_FROM_EMAIL

    email_args = dict(
        subject=subject,
        body=content,
        to=to,
        reply_to=[from_email]
    )
    if settings.ENVIRONMENT == "prod":
        message = EmailMessage(**email_args)
        message.content_subtype = 'html'
        message.send()
    else:
        print(email_args)
        


def email_project_admins(project, subject, body, from_email=None):
    project_admins = ProjectProfile.objects.filter(
        project_id=project, role=ProjectProfile.ADMIN).select_related('profile')

    if project_admins.count() > 0:
        mermaid_email(
            subject=subject,
            heading=project.name,
            subheading='MERMAID Project Administrator Communication',
            body=body,
            to=[p.profile.email for p in project_admins],
            from_email=[from_email]
        )


# for hooking up to https://api.datamermaid.org/contact_project?project_id=2c56b92b-ba1c-491f-8b62-23b1dc728890
def contact_project_admins(project, subject, body, from_email):
    # lots of checking/validation/antispam here
    # email_project_admins(project, subject, body, from_email)
    pass
