import operator

from django.core import serializers
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from .attributes import *
from .notifications import *
from .revision import *
from .summaries import *
from ..covariates import update_site_covariates_threaded
from ..models import *
from ..submission.utils import validate
from ..submission.validations import SiteValidation, ManagementValidation
from ..utils import get_subclasses
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


@receiver(post_save, sender=Site)
def run_site_validation(sender, instance, *args, **kwargs):
    if instance.project is None:
        return

    # validate(SiteValidation, Site, {"project_id": instance.project_id})

    if "created" in kwargs:
        # Need to update cached instance to keep
        # PUT/POST responses up to date.
        site = Site.objects.get(id=instance.id)
        instance.validations = site.validations
        instance.updated_on = site.updated_on


@receiver(post_save, sender=Management)
def run_management_validation(sender, instance, *args, **kwargs):
    if instance.project is None:
        return

    # validate(ManagementValidation, Management, {"project_id": instance.project_id})

    if "created" in kwargs:
        # Need to update cached instance to keep
        # PUT/POST responses up to date.
        mgmt = Management.objects.get(id=instance.id)
        instance.validations = mgmt.validations
        instance.updated_on = mgmt.updated_on


@receiver(pre_save, sender=Site)
def update_with_covariates(sender, instance, *args, **kwargs):
    update_site_covariates_threaded(instance)
