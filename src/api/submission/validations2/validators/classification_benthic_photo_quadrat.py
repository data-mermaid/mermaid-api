from itertools import repeat
from typing import Tuple

from django.db.models import Count

from ....models import Annotation, Classifier, Image
from .base import ERROR, OK, WARN, BaseValidator, validate_list, validator_result


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
        self._cache_quadrat_num_lookup = None

    @validator_result
    def __call__(self, collect_record_image: Tuple[dict, Image], **kwargs):
        collect_record, image = collect_record_image
        if isinstance(image, Image) is False:
            raise ValueError("ImageValidator only accepts Image instances")

        image_id = str(image.pk)
        if self._cache_quadrat_num_lookup is None:
            self._cache_quadrat_num_lookup = {
                str(image.id): quad_num + 1
                for quad_num, image in enumerate(
                    Image.objects.filter(collect_record_id=image.collect_record_id)
                )
            }

        context = {
            "image_id": image_id,
            "quadrat_num": self._cache_quadrat_num_lookup[image_id],
            "missing_num_annotations": None,
        }

        annos = Annotation.objects.select_related("point", "point__image").filter(
            is_confirmed=True, point__image_id=image_id
        )

        classifier = Classifier.objects.get_or_none(id=collect_record.get("classifier_id"))
        if not classifier:
            classifier = Classifier.latest()
            if not classifier:
                return OK, None, [context]

        num_points = classifier.num_points

        if not annos.exists():
            context["missing_num_annotations"] = num_points
            return ERROR, self.WRONG_NUM_CONFIRMED_ANNOS, [context]

        wrong_num_annos = (
            annos.values("point__image_id")
            .annotate(annotation_count=Count("id"))
            .exclude(annotation_count=num_points)
        )

        if wrong_num_annos.exists():
            context["missing_num_annotations"] = num_points - wrong_num_annos[0]["annotation_count"]
            return ERROR, self.WRONG_NUM_CONFIRMED_ANNOS, context

        return OK, None, context


class CollectRecordImagesValidator(BaseValidator):
    def __init__(
        self,
        **kwargs,
    ):
        super().__init__(**kwargs)

    @validate_list
    def __call__(self, collect_record, **kwargs):
        cr_id = collect_record.get("id")
        images = Image.objects.filter(collect_record_id=cr_id).order_by("created_on")
        return ImageValidator(), zip(repeat(collect_record), images)
