from collections import defaultdict

from django.conf import settings
from django.db.models import Q

from ..models import CollectRecord, Notification, ProjectProfile
from ..utils.email import emails_with_accounts, mermaid_email
from ..utils.notification import _suppress_notifications, add_notification


def notify_project_users(
    project,
    subject,
    email_template,
    notify_template,
    context,
    user_filters=None,
    extra_profiles=None,
):
    if _suppress_notifications.get():
        return
    filters = Q(project_id=project)
    if user_filters:
        filters &= user_filters
    project_users = ProjectProfile.objects.filter(filters).select_related("profile")
    project_profiles = [p.profile for p in project_users]
    if extra_profiles:
        project_profiles.extend(extra_profiles)

    if len(project_profiles) > 0:
        add_notification(subject, Notification.INFO, notify_template, context, project_profiles)

        project_emails = emails_with_accounts(project_profiles)
        if project_emails:
            mermaid_email(
                subject=subject,
                template=email_template,
                to=project_emails,
                context=context,
                from_email=settings.DEFAULT_FROM_EMAIL,
                reply_to=project_emails,
            )


def notify_profile(profile, subject, email_template, notify_template, context, reply_to=None):
    """Notify a single profile, emailing them whether or not they have an account."""
    if _suppress_notifications.get():
        return
    add_notification(subject, Notification.INFO, notify_template, context, [profile])
    if profile.email:
        mermaid_email(
            subject=subject,
            template=email_template,
            to=[profile.email],
            context=context,
            from_email=settings.DEFAULT_FROM_EMAIL,
            reply_to=reply_to,
        )


def notify_crs_transferred(project, from_profile, to_profile, admin_profile):
    project_name = project.name
    subject = f"{project_name} unsubmitted Sample Units transferred"
    context = {"project_name": project_name, "admin_profile": admin_profile}

    if admin_profile != from_profile:
        notify_template = "notifications/crs_transferred_away.txt"
        email_template = "emails/crs_transferred_away.txt"
        context["to_profile"] = to_profile
        add_notification(subject, Notification.INFO, notify_template, context, [from_profile])
        to_emails = emails_with_accounts([from_profile])
        if to_emails:
            mermaid_email(
                subject=subject,
                template=email_template,
                to=to_emails,
                context=context,
                from_email=settings.DEFAULT_FROM_EMAIL,
                reply_to=[admin_profile.email],
            )

    if admin_profile != to_profile:
        notify_template = "notifications/crs_transferred_to.txt"
        email_template = "emails/crs_transferred_to.txt"
        context["from_profile"] = from_profile
        add_notification(subject, Notification.INFO, notify_template, context, [to_profile])
        to_emails = emails_with_accounts([to_profile])
        if to_emails:
            mermaid_email(
                subject=subject,
                template=email_template,
                to=to_emails,
                context=context,
                from_email=settings.DEFAULT_FROM_EMAIL,
                reply_to=[admin_profile.email],
            )


def notify_admins_project_change(instance, text_changes):
    subject = f"Changes to {instance.name}"
    collect_project_url = f"{settings.DEFAULT_DOMAIN_COLLECT}/projects/{instance.pk}/project-info"

    context = {
        "project_name": instance.name,
        "profile": instance.updated_by,
        "collect_project_url": collect_project_url,
        "text_changes": text_changes,
    }
    email_template = "emails/admins_project_change.html"
    notify_template = "notifications/admins_project_change.txt"
    admins = Q(role=ProjectProfile.ADMIN)

    notify_project_users(
        instance, subject, email_template, notify_template, context, user_filters=admins
    )


def notify_admins_change(instance, changetype):
    if changetype == "add":
        subject_snippet = "added to"
        body_snippet = "given to"
    elif changetype == "remove":
        subject_snippet = "removed from"
        body_snippet = "removed from"
    else:
        return

    subject = f"Project administrator {subject_snippet} {instance.project.name}"
    collect_project_url = f"{settings.DEFAULT_DOMAIN_COLLECT}/projects/{instance.project.pk}/users"

    context = {
        "project_name": instance.project.name,
        "profile": instance.profile,
        "admin_profile": instance.updated_by,
        "collect_project_url": collect_project_url,
        "body_snippet": body_snippet,
    }
    email_template = "emails/admins_admins_change.html"
    notify_template = "notifications/admins_admins_change.txt"
    admins = Q(Q(role=ProjectProfile.ADMIN) | Q(id=instance.id))

    notify_project_users(
        instance.project,
        subject,
        email_template,
        notify_template,
        context,
        user_filters=admins,
    )


def notify_cr_owners_site_mr_deleted(instance, deleted_by_user):
    lookup = f"data__sample_event__{instance._meta.model_name}"
    collect_records = CollectRecord.objects.filter(**{lookup: instance.pk})
    deleted_by = "An unknown user"
    if deleted_by_user:
        deleted_by = deleted_by_user.full_name
    cr_profiles = defaultdict(int)
    for cr in collect_records:
        cr_profiles[cr.profile] += 1

    for profile, cr_count in cr_profiles.items():
        count = f"{cr_count} unsubmitted sample unit"
        if cr_count > 1:
            count = f"{count}s"
        context = {
            "site_mr": instance._meta.verbose_name,
            "site_mr_name": instance.name,
            "project_name": instance.project.name,
            "deleted_by": deleted_by,
            "cr_count": count,
        }
        notify_template = "notifications/site_mr_deleted.txt"

        add_notification(
            f"Site {instance.name} deleted from {instance.project.name}",
            Notification.WARNING,
            notify_template,
            context,
            [profile],
        )
