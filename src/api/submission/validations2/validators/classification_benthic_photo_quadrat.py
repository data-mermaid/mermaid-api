from collections import defaultdict

from ....models import Annotation, Classifier, Image
from .base import ERROR, OK, WARN, BaseValidator, validate_list, validator_result
from .region import BaseRegionValidator


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


class BaseAnnotationValidator(BaseValidator):
    def get_rows(self, collect_record, **kwargs):
        cr_id = collect_record.get("id")

        num_points_per_quadrat = (collect_record["data"].get("quadrat_transect") or {}).get(
            "num_points_per_quadrat"
        )
        if not num_points_per_quadrat:
            num_points_per_quadrat = Classifier.latest().num_points

        annos = (
            Annotation.objects.select_related("point", "point__image")
            .filter(point__image__collect_record_id=cr_id)
            .order_by(
                "point__image__created_on",
                "point_id",
                "-is_confirmed",
                "-score",
                "benthic_attribute__name",
                "growth_form__name",
            )
        )

        images = defaultdict(
            lambda: defaultdict(
                lambda: {
                    "image_id": None,
                    "attribute": None,
                    "growth_form": None,
                    "confirmed": 0,
                    "unconfirmed": 0,
                }
            )
        )
        points = set()

        for anno in annos:
            image_id = str(anno.point.image_id)
            point_id = str(anno.point_id)
            benthic_attribute_id = str(anno.benthic_attribute_id)
            growth_form_id = str(anno.growth_form.id) if anno.growth_form else ""
            uid = f"{image_id}::{benthic_attribute_id}::{growth_form_id}"

            images[image_id][uid]["image_id"] = image_id
            if anno.is_confirmed:
                images[image_id][uid]["confirmed"] += 1
                images[image_id][uid]["attribute"] = anno.benthic_attribute.id
                images[image_id][uid]["growth_form"] = (
                    anno.growth_form.id if anno.growth_form else ""
                )
                points.add(point_id)
            elif point_id not in points:
                images[image_id][uid]["unconfirmed"] += 1
                images[image_id][uid]["attribute"] = anno.benthic_attribute.id
                images[image_id][uid]["growth_form"] = (
                    anno.growth_form.id if anno.growth_form else ""
                )
                points.add(point_id)

        rows = []
        for image_id, groups in images.items():
            num_unconfirmed = 0
            num_confirmed = 0
            image_rows = []
            for uid, values in groups.items():
                image_rows.append(
                    {
                        "id": uid,
                        "image_id": image_id,
                        "attribute": values["attribute"],
                        "growth_form": values["growth_form"],
                        "confirmed": values["confirmed"],
                        "unconfirmed": values["unconfirmed"],
                        "is_unclassified": False,
                    }
                )
                if values["unconfirmed"] > 0:
                    num_unconfirmed += values["unconfirmed"]
                else:
                    num_confirmed += values["confirmed"]

            unclassified = num_points_per_quadrat - num_unconfirmed - num_confirmed

            if unclassified != 0:
                uid = f"{image_id}::::"
                image_rows.append(
                    {
                        "id": uid,
                        "image_id": image_id,
                        "attribute": None,
                        "growth_form": None,
                        "confirmed": 0,
                        "unconfirmed": 0,
                        "is_unclassified": True,
                    }
                )

            rows.extend(image_rows)

        return rows


class AnnotationConfirmedValidator(BaseValidator):
    UNCONFIRMED_ANNOTATION = "unconfirmed_annotation"
    unique_identifier_key = "id"
    group_key = "image_id"

    @validator_result
    def __call__(self, record, **kwargs):
        context = {
            "observation_id": record[self.unique_identifier_key],
            "group_id": record[self.group_key],
        }
        if record["unconfirmed"] > 0:
            return ERROR, self.UNCONFIRMED_ANNOTATION, context

        return OK, None, context


class ListAnnotationConfirmedValidator(BaseAnnotationValidator):
    def __init__(
        self,
        **kwargs,
    ):
        super().__init__(**kwargs)

    @validate_list
    def __call__(self, collect_record, **kwargs):
        rows = self.get_rows(collect_record)
        return AnnotationConfirmedValidator(), rows


class AnnotationUnclassifiedValidator(BaseValidator):
    UNCLASSIFIED_ANNOTATION = "unclassified_annotation"
    unique_identifier_key = "id"
    group_key = "image_id"

    @validator_result
    def __call__(self, record, **kwargs):
        context = {
            "observation_id": record[self.unique_identifier_key],
            "group_id": record[self.group_key],
        }
        if record["is_unclassified"]:
            return ERROR, self.UNCLASSIFIED_ANNOTATION, context

        return OK, None, context


class ListAnnotationUnclassifiedValidator(BaseAnnotationValidator):
    def __init__(
        self,
        **kwargs,
    ):
        super().__init__(**kwargs)

    @validate_list
    def __call__(self, collect_record, **kwargs):
        rows = self.get_rows(collect_record)
        return AnnotationUnclassifiedValidator(), rows


class AnnotationRegionValidator(BaseAnnotationValidator, BaseRegionValidator):
    group_context_key = "image_id"

    def get_observation_ids_and_attribute_ids(self, observations):
        observation_ids = []
        attribute_ids = []
        for obs in observations:
            if not obs.get("id"):
                continue
            observation_ids.append(obs.get("id"))
            attribute_ids.append(obs.get("attribute"))

        return observation_ids, attribute_ids

    def get_records(self, collect_record, **kwargs):
        return self.get_rows(collect_record)
