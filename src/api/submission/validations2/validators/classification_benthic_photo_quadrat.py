from django.db.models import Count

from ....models import Annotation, Image
from .base import ERROR, OK, WARN, BaseValidator, validator_result, validate_list


class ImageCountValidator(BaseValidator):
    DIFFERENT_NUMBER_OF_IMAGES = "diff_num_images"

    def __init__(
        self,
        num_quadrats_path,
        **kwargs,
    ):
        self.num_quadrats_path = num_quadrats_path
        super().__init__(**kwargs)

    @validator_result
    def __call__(self, collect_record, **kwargs):
        cr_id = collect_record.get("id")
        num_quadrats = self.get_value(collect_record, self.num_quadrats_path)
        num_images = Image.objects.filter(collect_record_id=cr_id).count()

        if num_images != num_quadrats:
            return WARN, self.DIFFERENT_NUMBER_OF_IMAGES

        return OK


class ImageValidator(BaseValidator):
    WRONG_NUM_CONFIRMED_ANNOS = "wrong_num_confirmed_annos"

    def __init__(
        self,
        **kwargs,
    ):
        super().__init__(**kwargs)

    @validator_result
    def __call__(self, *args, **kwargs):
        image = args[0]
        if isinstance(image, Image) is False:
            raise ValueError("ImageValidator only accepts Image instances")

        image_id = str(image.pk)
        annos = Annotation.objects.select_related("point", "point__image").filter(
            is_confirmed=True, point__image_id=image_id
        )

        classifier = annos[0].classifier
        wrong_num_annos = (
            annos.values("point__image_id")
            .annotate(annotation_count=Count("id"))
            .exclude(annotation_count=classifier.num_points)
        )

        if not wrong_num_annos:
            return OK, None, {"image_id": image_id}

        return WARN, self.WRONG_NUM_CONFIRMED_ANNOS, {"image_id": image_id}


class CollectRecordImagesValidator(BaseValidator):
    def __init__(
        self,
        **kwargs,
    ):
        super().__init__(**kwargs)

    @validate_list
    def __call__(self, collect_record, **kwargs):
        cr_id = collect_record.get("id")
        images = Image.objects.filter(collect_record_id=cr_id)
        return ImageValidator(), images
