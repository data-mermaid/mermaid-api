from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from ..models import CollectRecord, Image
from ..utils import classification as cls_utils
from .submission import post_edit, post_submit


@receiver(pre_save, sender=Image)
def pre_image_save(sender, instance, **kwargs):
    if not instance.created_on:
        try:
            cls_utils.check_if_valid_image(instance)
            cls_utils.store_exif(instance)
            instance.original_image_name = instance.image.name
            instance.original_image_width = instance.image.width
            instance.original_image_height = instance.image.height

            image_name = f"{instance.id}.png"
            instance.name = image_name
            instance.image.name = image_name

            cls_utils.correct_image_orientation(instance)
        except Exception:
            raise


@receiver(post_delete, sender=Image)
def delete_images_on_model_delete(sender, instance, **kwargs):
    if instance.image:
        instance.image.delete(save=False)
    if instance.thumbnail:
        instance.thumbnail.delete(save=False)
    if instance.annotations_file:
        instance.annotations_file.delete(save=False)


@receiver(post_save, sender=Image)
def post_save_classification_image(sender, instance, created, **kwargs):
    if not instance.thumbnail:
        needs_new_thumbnail = True
    else:
        img_checksum = cls_utils.create_image_checksum(instance.image)
        original_img_record = Image.objects.get(pk=instance.pk)
        needs_new_thumbnail = img_checksum != original_img_record.original_image_checksum

    if needs_new_thumbnail:
        thumb_file = cls_utils.create_thumbnail(instance)
        instance.original_image_checksum = cls_utils.create_image_checksum(instance.image)
        # Saving thumbnail (save=True), causes double save but it's necessary
        # to have thumbnail created and saved in the post_save so thumbnails
        # don't get orphaned if done in a pre_save signal.
        instance.thumbnail.save(thumb_file.name, thumb_file, save=True)


@receiver(post_submit, sender=CollectRecord)
def create_image_annotations_files(sender, instance, **kwargs):
    if not instance.data or not instance.data.get("image_classification"):
        return

    for img in Image.objects.filter(collect_record_id=instance.id):
        img.create_annotations_file()


@receiver(post_edit, sender=CollectRecord)
def delete_image_annotations_files(sender, instance, **kwargs):
    if not instance.data or not instance.data.get("image_classification"):
        return

    for img in Image.objects.filter(collect_record_id=instance.id):
        if img.annotations_file:
            img.annotations_file.delete(save=False)
            img.annotations_file = None
            img.save()
