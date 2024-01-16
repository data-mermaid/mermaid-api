from django.core.management import call_command
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from ..models import (
    SUPERUSER_APPROVED,
    BenthicAttribute,
    FishFamily,
    FishGenus,
    FishGrouping,
    FishSpecies,
    GrowthForm,
    Region,
)
from ..utils.q import submit_job
from ..utils.reports import update_attributes_report

benthic_models = [BenthicAttribute, GrowthForm, Region]
fish_models = [FishGrouping, FishFamily, FishGenus, FishSpecies, Region]


@receiver(post_delete, sender=BenthicAttribute)
@receiver(post_save, sender=BenthicAttribute)
@receiver(post_delete, sender=FishFamily)
@receiver(post_save, sender=FishFamily)
@receiver(post_delete, sender=FishGenus)
@receiver(post_save, sender=FishGenus)
@receiver(post_delete, sender=FishGrouping)
@receiver(post_save, sender=FishGrouping)
@receiver(post_delete, sender=FishSpecies)
@receiver(post_save, sender=FishSpecies)
@receiver(post_delete, sender=Region)
@receiver(post_save, sender=Region)
@receiver(post_save, sender=GrowthForm)
def refresh_attribute_views(sender, instance, **kwargs):
    if sender in fish_models:
        print("refresh fish")
        call_command("refresh_view", "mv_fish_attributes")

    if sender in benthic_models:
        print("refresh benthic")

    if (
        isinstance(instance, Region)
        or isinstance(instance, GrowthForm)
        or instance.status == SUPERUSER_APPROVED
    ):
        submit_job(10, update_attributes_report)
