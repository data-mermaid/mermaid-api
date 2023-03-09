from django import urls
from django.conf import settings
from django.db.models.signals import post_delete, post_save, m2m_changed
from django.dispatch import receiver

from ..models import BaseAttributeModel, Tag, ProjectProfile, Project
from ..notifications import (
    notify_admins_change,
    notify_admins_project_change,
    notify_project_users,
)
from ..utils import get_subclasses
from ..utils.email import mermaid_email


__all__ = (
    "notify_admins_project_instance_change",
    "notify_admins_project_tags_change",
    "notify_admins_new_admin",
    "notify_removed_project_user",
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


@receiver(post_save, sender=ProjectProfile)
def notify_admins_new_admin(sender, instance, created, **kwargs):
    if instance.role >= ProjectProfile.ADMIN:
        notify_admins_change(instance, "add")
    elif not created and hasattr(instance, "_old_values"):
        old_role = instance._old_values.get("role")
        if old_role >= ProjectProfile.ADMIN:
            notify_admins_change(instance, "remove")


@receiver(post_save, sender=ProjectProfile)
def notify_new_project_user(sender, instance, created, **kwargs):
    if created is False:
        return

    subject = f"User added to {instance.project.name}"
    context = {
        "project_profile": instance,
        "admin_profile": instance.updated_by,
        "added_removed": "added to",
    }
    if instance.profile.num_account_connections == 0:
        email_template = "emails/new_user_added_to_project.html"
    else:
        email_template = "emails/user_project_add_remove.html"
    notify_template = "notifications/user_project_add_remove.txt"

    notify_project_users(
        instance.project, subject, email_template, notify_template, context
    )


@receiver(post_delete, sender=ProjectProfile)
def notify_removed_project_user(sender, instance, **kwargs):
    subject = f"User removed from {instance.project.name}"
    context = {
        "project_profile": instance,
        "admin_profile": instance.updated_by,
        "added_removed": "removed from",
    }
    email_template = "emails/user_project_add_remove.html"
    notify_template = "notifications/user_project_add_remove.txt"
    self = [instance.profile]

    notify_project_users(
        instance.project,
        subject,
        email_template,
        notify_template,
        context,
        extra_profiles=self,
    )
