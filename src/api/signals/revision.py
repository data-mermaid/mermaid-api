from django.db.models.signals import (
    m2m_changed,
    post_delete,
    post_save,
    pre_delete,
    pre_save,
)
from django.dispatch import receiver

from ..models import AuthUser, CollectRecord, Profile, ProjectProfile, Revision


def _create_project_profile_revisions(query_kwargs):
    for project_profile in ProjectProfile.objects.filter(**query_kwargs):
        Revision.create_from_instance(project_profile)


@receiver(post_save, sender=Profile)
def update_project_profile_revisions(sender, instance, *args, **kwargs):
    _create_project_profile_revisions({"profile": instance})


@receiver(post_save, sender=CollectRecord)
def new_collect_record(sender, instance, created, *args, **kwargs):
    if created:
        _create_project_profile_revisions(
            {"profile": instance.profile, "project": instance.project}
        )


@receiver(pre_delete, sender=CollectRecord)
def deleted_collect_record(sender, instance, created, *args, **kwargs):
    _create_project_profile_revisions(
        {"profile": instance.profile, "project": instance.project}
    )


@receiver(post_save, sender=AuthUser)
def new_auth_user(sender, instance, created, *args, **kwargs):
    if created:
        _create_project_profile_revisions({"profile": instance.profile})


@receiver(pre_delete, sender=AuthUser)
def deleted_auth_user(sender, instance, created, *args, **kwargs):
    _create_project_profile_revisions({"profile": instance.profile})
