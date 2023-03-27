from django.core.cache import cache
from django.db.models.signals import post_delete, post_save, pre_delete
from django.dispatch import receiver

from ..models import (
    AuthUser,
    CollectRecord,
    Profile,
    ProjectProfile,
    Revision,
    FishFamily,
    FishGenus,
    FishSpecies,
    BenthicAttribute,
)
from ..resources.sync.views import (
    FISH_SPECIES_SOURCE_TYPE,
    FISH_GENERA_SOURCE_TYPE,
    FISH_FAMILIES_SOURCE_TYPE,
    BENTHIC_ATTRIBUTES_SOURCE_TYPE,
)


__all__ = (
    "update_project_profile_revisions",
    "delete_project_profile_revisions",
    "update_project_profile_revisions",
    "new_collect_record",
    "deleted_collect_record",
    "new_auth_user",
    "deleted_auth_user",
    "bust_revision_cache",
)


def _create_project_profile_revisions(query_kwargs):
    for project_profile in ProjectProfile.objects.filter(**query_kwargs):
        Revision.create_from_instance(project_profile)


@receiver(pre_delete, sender=ProjectProfile)
def delete_project_profile_revisions(sender, instance, *args, **kwargs):
    Revision.create_from_instance(instance.project)
    Revision.create_from_instance(instance, related_to_profile_id=instance.profile.pk)
    Revision.create_from_instance(instance.project, related_to_profile_id=instance.profile.pk)


@receiver(post_save, sender=ProjectProfile)
def update_project_profile_revisions(sender, instance, *args, **kwargs):
    Revision.create_from_instance(instance.project)


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
def deleted_collect_record(sender, instance, *args, **kwargs):
    _create_project_profile_revisions(
        {"profile": instance.profile, "project": instance.project}
    )


@receiver(post_save, sender=AuthUser)
def new_auth_user(sender, instance, created, *args, **kwargs):
    if created:
        _create_project_profile_revisions({"profile": instance.profile})


@receiver(pre_delete, sender=AuthUser)
def deleted_auth_user(sender, instance, *args, **kwargs):
    _create_project_profile_revisions({"profile": instance.profile})


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
