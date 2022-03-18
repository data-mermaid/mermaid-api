import operator

from django import urls
from django.conf import settings
from django.core import serializers
from django.core.cache import cache
from django.db.models.signals import post_delete, post_save, pre_delete, pre_save, m2m_changed
from django.dispatch import receiver

from . import revision
from . import summaries
from ..covariates import update_site_covariates_in_thread
from ..models import *
from ..resources.sync.views import (
    BENTHIC_ATTRIBUTES_SOURCE_TYPE,
    FISH_FAMILIES_SOURCE_TYPE,
    FISH_GENERA_SOURCE_TYPE,
    FISH_SPECIES_SOURCE_TYPE,
)
from ..submission.utils import validate
from ..submission.validations import SiteValidation, ManagementValidation
from ..utils import get_subclasses
from ..utils.email import email_project_admins, mermaid_email
from ..utils.sample_units import (
    delete_orphaned_sample_unit,
    delete_orphaned_sample_event,
)


def backup_model_record(sender, instance, using, **kwargs):
    try:
        if (
            instance._meta.app_label != "api"
            or instance._meta.model_name == "archivedrecord"
            or not isinstance(instance.pk, uuid.UUID)
        ):
            return

        project_pk = None
        if hasattr(instance, "project_lookup"):
            project_lookup = instance.project_lookup.split("__")
            project = operator.attrgetter(".".join(project_lookup))(instance)
            project_pk = project.pk

        data = serializers.serialize("json", [instance])
        record = dict(
            app_label=instance._meta.app_label,
            model=instance._meta.model_name,
            record_pk=instance.pk,
            project_pk=project_pk,
            record=json.loads(data)[0],
        )
        ArchivedRecord.objects.create(**record)
    except Exception as err:
        logger.exception(err)


def set_created_by(sender, instance, **kwargs):
    if instance._meta.app_label != "api":
        return

    if (
        instance.updated_on is None
        and hasattr(instance, "updated_by")
        and getattr(instance, "updated_by") is not None
    ):
        instance.created_by = instance.updated_by


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

    mermaid_email(subject, template, [settings.SUPERUSER[1]], context=context)


for c in get_subclasses(BaseModel):
    pre_save.connect(
        set_created_by,
        sender=c,
        dispatch_uid="{}_set_created_by".format(c._meta.object_name),
    )
    post_delete.connect(
        backup_model_record,
        sender=c,
        dispatch_uid="{}_delete_archive".format(c._meta.object_name),
    )

for c in get_subclasses(BaseAttributeModel):
    post_save.connect(
        email_superadmin_on_new, sender=c, dispatch_uid=f"{c._meta.object_name}_save"
    )
post_save.connect(
    email_superadmin_on_new, sender=Tag, dispatch_uid=f"{Tag._meta.object_name}_save"
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
    template = "emails/admins_project_change.html"

    email_project_admins(instance, subject, template, context)


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
            text_changes.append(f"Old {fname}: {oldval}\nNew {fname}: {newval}")

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
    collect_project_url = (
        f"https://{settings.DEFAULT_DOMAIN_COLLECT}/#/projects/{instance.project.pk}/users"
    )

    context = {
        "project_name": instance.project.name,
        "profile": instance.profile,
        "admin_profile": instance.updated_by,
        "collect_project_url": collect_project_url,
        "body_snippet": body_snippet,
    }
    template = "emails/admins_admins_change.html"

    email_project_admins(instance.project, subject, template, context)


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

    mermaid_email(f"New User added to {instance.project.name}", template, [instance.profile.email], context=context)


# Don't need to iterate over TransectMethod subclasses because TransectMethod is not abstract
@receiver(post_delete, sender=TransectMethod, dispatch_uid="TransectMethod_delete_su")
def del_orphaned_su(sender, instance, *args, **kwargs):
    if instance.sample_unit is not None:
        delete_orphaned_sample_unit(instance.sample_unit, instance)


def del_orphaned_se(sender, instance, *args, **kwargs):
    delete_orphaned_sample_event(instance.sample_event, instance)


for suclass in get_subclasses(SampleUnit):
    classname = suclass._meta.object_name

    post_delete.connect(
        del_orphaned_se, sender=suclass, dispatch_uid=f"{classname}_delete_se"
    )


@receiver(post_delete, sender=Site)
@receiver(post_save, sender=Site)
def run_site_validation(sender, instance, *args, **kwargs):
    if instance.project is None:
        return

    validate(SiteValidation, Site, {"project_id": instance.project_id})

    if "created" in kwargs:
        # Need to update cached instance to keep
        # PUT/POST responses up to date.
        site = Site.objects.get(id=instance.id)
        instance.validations = site.validations
        instance.updated_on = site.updated_on


@receiver(post_delete, sender=Management)
@receiver(post_save, sender=Management)
def run_management_validation(sender, instance, *args, **kwargs):
    if instance.project is None:
        return

    validate(ManagementValidation, Management, {"project_id": instance.project_id})

    if "created" in kwargs:
        # Need to update cached instance to keep
        # PUT/POST responses up to date.
        mgmt = Management.objects.get(id=instance.id)
        instance.validations = mgmt.validations
        instance.updated_on = mgmt.updated_on


@receiver(post_delete, sender=CollectRecord)
@receiver(post_save, sender=CollectRecord)
def run_cr_management_validation(sender, instance, *args, **kwargs):
    if instance.project is None:
        return

    data = instance.data or {}
    if "sample_event" in data:
        mrid = data["sample_event"].get("management")
        if mrid is not None:
            validate(
                ManagementValidation, Management, {"project_id": instance.project_id}
            )


@receiver(pre_save, sender=Site)
def update_with_covariates(sender, instance, *args, **kwargs):
    update_site_covariates(instance)


@receiver(post_save, sender=FishFamily)
@receiver(post_delete, sender=FishFamily)
@receiver(post_save, sender=FishGenus)
@receiver(post_delete, sender=FishGenus)
@receiver(post_save, sender=FishSpecies)
@receiver(post_delete, sender=FishSpecies)
@receiver(post_save, sender=BenthicAttribute)
@receiver(post_delete, sender=BenthicAttribute)
def bust_revision_cache(sender, instance, *args, **kwargs):
    if sender in (FishSpecies, FishGenus, FishFamily):
        cache.delete(FISH_SPECIES_SOURCE_TYPE)
        cache.delete(FISH_GENERA_SOURCE_TYPE)
        cache.delete(FISH_FAMILIES_SOURCE_TYPE)
    elif sender == BenthicAttribute:
        cache.delete(BENTHIC_ATTRIBUTES_SOURCE_TYPE)
