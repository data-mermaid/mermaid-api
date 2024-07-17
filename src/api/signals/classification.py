from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from ..models import Image
from ..utils import classification as cls_utils


@receiver(pre_save, sender=Image)
def strip_exif(sender, instance, **kwargs):
    if not instance.created_on:
        cls_utils.store_exif(instance)
        original_image_name = instance.image.name
        instance.data = instance.data or {}
        if "original_image_name" not in instance.data:
            instance.data["original_image_name"] = original_image_name

        image_name = cls_utils.create_unique_image_name(instance.image)
        instance.name = image_name
        instance.image.name = image_name

        cls_utils.correct_image_orientation(instance)
        cls_utils.update_exif(instance)


@receiver(post_delete, sender=Image)
def delete_images_on_model_delete(sender, instance, **kwargs):
    if instance.image:
        instance.image.delete(save=False)
    if instance.thumbnail:
        instance.thumbnail.delete(save=False)


@receiver(post_save, sender=Image)
def post_save_classification_image(sender, instance, created, **kwargs):
    if not instance.thumbnail:
        needs_new_thumbnail = True
    else:
        img_checksum = cls_utils.create_image_checksum(instance.image)
        original_img_record = Image.objects.get(pk=instance.pk)
        needs_new_thumbnail = img_checksum != original_img_record.original_image_checksum

    if needs_new_thumbnail:
        thumb_file = cls_utils.create_thumbnail(instance.image)
        instance.original_image_checksum = cls_utils.create_image_checksum(instance.image)
        # Saving thumbnail (save=True), causes double save but it's necessary
        # to have thumbnail created and saved in the post_save so thumbnails
        # don't get orphaned if done in a pre_save signal.
        instance.thumbnail.save(thumb_file.name, thumb_file, save=True)
