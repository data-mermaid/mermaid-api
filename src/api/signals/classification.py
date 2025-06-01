import logging

from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from ..models import Classifier, CollectRecord, Image
from ..utils import classification as cls_utils
from .submission import post_edit, post_submit

logger = logging.getLogger(__name__)


@receiver(pre_save, sender=Image)
def pre_image_save(sender, instance, **kwargs):
    if not instance.created_on:
        try:
            cls_utils.check_if_valid_image(instance)

            try:
                cls_utils.store_exif(instance)
            except Exception:
                logger.exception("Error storing EXIF data")

            instance.original_image_name = instance.image.name
            image_name = f"{instance.id}.png"
            instance.name = image_name
            instance.image.name = image_name

            cls_utils.save_normalized_imagefile(instance)
            # original_* dimensions refer to width/height after correcting for orientation
            # i.e. original width/height of the image taken with a 'camera on its side'
            instance.original_image_width = instance.image.width
            instance.original_image_height = instance.image.height
        except Exception:
            raise


@receiver(post_delete, sender=Image)
def delete_images_on_model_delete(sender, instance, **kwargs):
    if instance.image:
        instance.image.delete(save=False)
    if instance.thumbnail:
        instance.thumbnail.delete(save=False)
    if instance.feature_vector_file:
        instance.feature_vector_file.delete(save=False)
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


@receiver(pre_save, sender=CollectRecord)
def assign_classifier(sender, instance, **kwargs):
    if not instance.data or not instance.data.get("image_classification"):
        return

    classifier_id = instance.data.get("classifier_id")
    if classifier_id:
        return

    classifier = Classifier.latest()
    if "classifier_id" not in instance.data and classifier:
        instance.data["classifier_id"] = str(classifier.id)
        instance.data["quadrat_transect"]["num_points_per_quadrat"] = classifier.num_points


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
