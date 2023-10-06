from django.core.cache import cache
from django.db.models.signals import post_delete, post_save, pre_delete
from django.dispatch import receiver

from ..models import (
    AuthUser,
    BenthicAttribute,
    BenthicTransect,
    CollectRecord,
    FishBeltTransect,
    FishFamily,
    FishGenus,
    FishSpecies,
    Management,
    ObsBeltFish,
    ObsBenthicLIT,
    ObsBenthicPhotoQuadrat,
    ObsBenthicPIT,
    ObsColoniesBleached,
    ObsHabitatComplexity,
    ObsQuadratBenthicPercent,
    Observer,
    Profile,
    ProjectProfile,
    QuadratCollection,
    QuadratTransect,
    Revision,
    SampleEvent,
    Site,
    TransectMethod,
)
from ..resources.sync.views import (
    FISH_SPECIES_SOURCE_TYPE,
    FISH_GENERA_SOURCE_TYPE,
    FISH_FAMILIES_SOURCE_TYPE,
    BENTHIC_ATTRIBUTES_SOURCE_TYPE,
)
from ..utils.related import get_related_project


# ***************************************************************
# NOTE: Database triggers exist to populate revisions 
# if the following tables are inserted, deleted or updated:
#     * fish_species
#     * management
#     * api_collectrecord
#     * benthic_attribute
#     * fish_genus
#     * fish_family
#     * site
#     * project_profile
#     * project
# ***************************************************************


def _create_project_profile_revisions(query_kwargs):
    for project_profile in ProjectProfile.objects.filter(**query_kwargs):
        Revision.create_from_instance(project_profile)


@receiver(post_save, sender=Profile)
def update_profile_revisions(sender, instance, *args, **kwargs):
    _create_project_profile_revisions({"profile": instance})


@receiver(pre_delete, sender=ProjectProfile)
def delete_project_profile_revisions(sender, instance, *args, **kwargs):
    Revision.create_from_instance(instance, related_to_profile_id=instance.profile.pk)
    Revision.create_from_instance(
        instance.project, related_to_profile_id=instance.profile.pk
    )


@receiver(post_save, sender=CollectRecord)
def new_collect_record_revisions(sender, instance, created, *args, **kwargs):
    if created:
        _create_project_profile_revisions(
            {"profile": instance.profile, "project": instance.project}
        )


@receiver(pre_delete, sender=CollectRecord)
def deleted_collect_record_revisions(sender, instance, *args, **kwargs):
    _create_project_profile_revisions(
        {"profile": instance.profile, "project": instance.project}
    )


@receiver(post_delete, sender=BenthicTransect)
@receiver(post_save, sender=BenthicTransect)
@receiver(post_delete, sender=CollectRecord)
@receiver(post_save, sender=CollectRecord)
@receiver(post_delete, sender=FishBeltTransect)
@receiver(post_save, sender=FishBeltTransect)
@receiver(post_delete, sender=Management)
@receiver(post_save, sender=Management)
@receiver(post_delete, sender=ObsBeltFish)
@receiver(post_save, sender=ObsBeltFish)
@receiver(post_delete, sender=ObsBenthicPhotoQuadrat)
@receiver(post_save, sender=ObsBenthicPhotoQuadrat)
@receiver(post_delete, sender=ObsBenthicLIT)
@receiver(post_save, sender=ObsBenthicLIT)
@receiver(post_delete, sender=ObsBenthicPIT)
@receiver(post_save, sender=ObsBenthicPIT)
@receiver(post_delete, sender=ObsColoniesBleached)
@receiver(post_save, sender=ObsColoniesBleached)
@receiver(post_delete, sender=ObsHabitatComplexity)
@receiver(post_save, sender=ObsHabitatComplexity)
@receiver(post_delete, sender=ObsQuadratBenthicPercent)
@receiver(post_save, sender=ObsQuadratBenthicPercent)
@receiver(post_delete, sender=Observer)
@receiver(post_save, sender=Observer)
@receiver(post_delete, sender=ProjectProfile)
@receiver(post_save, sender=ProjectProfile)
@receiver(post_delete, sender=QuadratCollection)
@receiver(post_save, sender=QuadratCollection)
@receiver(post_delete, sender=QuadratTransect)
@receiver(post_save, sender=QuadratTransect)
@receiver(post_delete, sender=SampleEvent)
@receiver(post_save, sender=SampleEvent)
@receiver(post_delete, sender=Site)
@receiver(post_save, sender=Site)
@receiver(post_delete, sender=TransectMethod)
@receiver(post_save, sender=TransectMethod)
def update_project_updated_on(sender, instance, *args, **kwargs):
    project = get_related_project(instance)
    if project is not None:
        project.save()


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
