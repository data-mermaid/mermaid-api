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
from ..reports import attributes_report
from ..utils.reports import update_attributes_report
from ..utils.q import submit_job


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
def generate_attribute_report(sender, instance, **kwargs):
    if instance.status == SUPERUSER_APPROVED or isinstance(instance, Region):
        attributes_report.write_attribute_reference()
        submit_job(10, update_attributes_report)
