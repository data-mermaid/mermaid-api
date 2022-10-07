from django import urls
from django.conf import settings
from django.db.models.signals import post_delete, post_save, m2m_changed, pre_delete
from django.dispatch import receiver

from ..models import (
    BaseAttributeModel,
    Tag,
    ProjectProfile,
    Notification,
    Project,
)
from ..utils import get_subclasses
from ..utils.email import mermaid_email
from ..utils.notification import add_notification


__all__ = (
    "notify_admins_project_instance_change",
    "notify_admins_project_tags_change",
    "notify_admins_new_admin",
    "notify_admins_dropped_admin",
    "notify_new_project_user",
)


# send email if a new attribute/tag/etc. is created (not updated), AND it was created by a user (not via ingestion),
# AND it was not created by an admin
def email_superadmin_on_new(sender, instance, created, **kwargs):
    admin_emails = [e[1] for e in settings.ADMINS] + [settings.SUPERUSER[1]]
    instance_label = sender._meta.verbose_name or "instance"
    if (
        created is False
        or instance.updated_by is None
        or instance.updated_by.email in admin_emails
    ):
        return

    subject = (
        f"New {instance_label} proposed for MERMAID by {instance.updated_by.full_name}"
    )
    reverse_str = f"admin:{sender._meta.app_label}_{sender._meta.model_name}_change"
    url = urls.reverse(reverse_str, args=[instance.pk])
    admin_link = f"{settings.DEFAULT_DOMAIN_API}{url}"

    context = {
        "profile": instance.updated_by,
        "admin_link": admin_link,
        "attrib_name": str(instance),
        "instance_label": instance_label,
    }
    template = "emails/superadmins_new_attribute.html"

    mermaid_email(
        subject,
        template,
        [settings.SUPERUSER[1]],
        context=context,
        reply_to=instance.updated_by.email,
    )


for c in get_subclasses(BaseAttributeModel):
    post_save.connect(
        email_superadmin_on_new, sender=c, dispatch_uid=f"{c._meta.object_name}_save"
    )
post_save.connect(
    email_superadmin_on_new, sender=Tag, dispatch_uid=f"{Tag._meta.object_name}_save"
)


def notify_project_admins(
    project, subject, email_template, notify_template, context, from_email=None
):
    project_admins = ProjectProfile.objects.filter(
        project_id=project, role=ProjectProfile.ADMIN
    ).select_related("profile")
    project_admin_profiles = [p.profile for p in project_admins]

    if project_admins.count() > 0:
        add_notification(
            subject, Notification.INFO, notify_template, context, project_admin_profiles
        )

        project_admin_emails = [p.email for p in project_admin_profiles]
        from_email = from_email or settings.DEFAULT_FROM_EMAIL
        mermaid_email(
            subject,
            email_template,
            project_admin_emails,
            context=context,
            from_email=from_email,
            reply_to=project_admin_emails,
        )


def notify_admins_project_change(instance, text_changes):
    subject = f"Changes to {instance.name}"
    collect_project_url = (
        f"https://{settings.DEFAULT_DOMAIN_COLLECT}/#/projects/{instance.pk}/details"
    )

    context = {
        "project_name": instance.name,
        "profile": instance.updated_by,
        "collect_project_url": collect_project_url,
        "text_changes": text_changes,
    }
    email_template = "emails/admins_project_change.html"
    notify_template = "notifications/admins_project_change.txt"

    notify_project_admins(instance, subject, email_template, notify_template, context)


@receiver(post_save, sender=Project)
def notify_admins_project_instance_change(sender, instance, created, **kwargs):
    if created or not hasattr(instance, "_old_values"):
        return

    old_values = instance._old_values
    new_values = instance._new_values
    diffs = [
        (k, (v, new_values[k])) for k, v in old_values.items() if v != new_values[k]
    ]
    if diffs:
        text_changes = []
        for diff in diffs:
            field = sender._meta.get_field(diff[0])
            fname = field.verbose_name
            oldval = diff[1][0]
            newval = diff[1][1]
            if field.choices:
                oldval = dict(field.choices)[diff[1][0]]
                newval = dict(field.choices)[diff[1][1]]
            text_changes.append(f"Old {fname}: {oldval} New {fname}: {newval}")

        notify_admins_project_change(instance, text_changes)


@receiver(m2m_changed, sender=Project.tags.through)
def notify_admins_project_tags_change(
    sender, instance, action, reverse, model, pk_set, **kwargs
):
    if action == "post_add" or action == "post_remove":
        text_changes = []
        verb = ""
        if action == "post_add":
            verb = "Added"
        elif action == "post_remove":
            verb = "Removed"

        altered_tags = Tag.objects.filter(pk__in=pk_set)
        if altered_tags.count() > 0:
            for t in altered_tags:
                text_changes.append(f"{verb} organization: {t.name}")

            notify_admins_project_change(instance, text_changes)


def notify_admins_change(instance, changetype):
    if changetype == "add":
        subject_snippet = "added to"
        body_snippet = "given administrative privileges to"
    elif changetype == "remove":
        subject_snippet = "removed from"
        body_snippet = "removed from this project, or is no longer an administrator for"
    else:
        return

    subject = f"Project administrator {subject_snippet} {instance.project.name}"
    collect_project_url = f"https://{settings.DEFAULT_DOMAIN_COLLECT}/#/projects/{instance.project.pk}/users"

    context = {
        "project_name": instance.project.name,
        "profile": instance.profile,
        "admin_profile": instance.updated_by,
        "collect_project_url": collect_project_url,
        "body_snippet": body_snippet,
    }
    email_template = "emails/admins_admins_change.html"
    notify_template = "notifications/admins_admins_change.txt"

    notify_project_admins(
        instance.project, subject, email_template, notify_template, context
    )


@receiver(post_save, sender=ProjectProfile)
def notify_admins_new_admin(sender, instance, created, **kwargs):
    if instance.role >= ProjectProfile.ADMIN:
        notify_admins_change(instance, "add")
    elif not created and hasattr(instance, "_old_values"):
        old_role = instance._old_values.get("role")
        if old_role >= ProjectProfile.ADMIN:
            notify_admins_change(instance, "remove")


@receiver(post_delete, sender=ProjectProfile)
def notify_admins_dropped_admin(sender, instance, **kwargs):
    if instance.role >= ProjectProfile.ADMIN:
        notify_admins_change(instance, "remove")


@receiver(post_save, sender=ProjectProfile)
def notify_new_project_user(sender, instance, created, **kwargs):
    if created is False:
        return

    context = {
        "project_profile": instance,
        "admin_profile": instance.updated_by,
    }
    if instance.profile.num_account_connections == 0:
        template = "emails/new_user_added_to_project.html"
    else:
        template = "emails/user_added_to_project.html"

    mermaid_email(
        f"New User added to {instance.project.name}",
        template,
        [instance.profile.email],
        context=context,
    )
