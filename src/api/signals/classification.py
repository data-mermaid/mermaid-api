from django.db.models.signals import post_delete
from django.dispatch import receiver

from ..models import Image


@receiver(post_delete, sender=Image)
def delete_images_on_model_delete(sender, instance, **kwargs):
    if instance.image:
        instance.image.delete(save=False)
    if instance.thumbnail:
        instance.thumbnail.delete(save=False)
