from collections import defaultdict

from django.db.models import Prefetch, Q

from ....models import (
    Annotation,
    Classifier,
    CollectRecord,
    Image,
    ObsBenthicPhotoQuadrat,
)
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


class DuplicateImageValidator(BaseValidator):
    DUPLICATE_IMAGES = "duplicate_images"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @validator_result
    def __call__(self, collect_record, **kwargs):
        cr_id = collect_record.get("id")
        project_id = collect_record.get("project")
        if not project_id:
            return OK
        cr_images = Image.objects.filter(collect_record_id=cr_id)

        # Preload all duplicate candidates in project with matching checksums
        checksums = set(img.original_image_checksum for img in cr_images)
        duplicate_images = (
            Image.objects.filter(original_image_checksum__in=checksums)
            .filter(
                Q(
                    **{
                        f"obs_benthic_photo_quadrats__{ObsBenthicPhotoQuadrat.project_lookup}": project_id
                    }
                )
                | Q(
                    collect_record_id__in=CollectRecord.objects.filter(
                        project_id=project_id
                    ).values("id")
                )
            )
            .prefetch_related(
                Prefetch(
                    "obs_benthic_photo_quadrats",
                    queryset=ObsBenthicPhotoQuadrat.objects.only(
                        "image_id", "benthic_photo_quadrat_transect_id"
                    ),
                )
            )
            .distinct()
        )
        duplicates_by_checksum = defaultdict(list)
        for img in duplicate_images:
            benthicpqt_id = ""
            if img.obs_benthic_photo_quadrats.all():
                benthicpqt_id = str(
                    img.obs_benthic_photo_quadrats.all()[0].benthic_photo_quadrat_transect_id
                )
            collect_record_id = ""
            if img.collect_record_id:
                collect_record_id = str(img.collect_record_id)

            duplicates_by_checksum[img.original_image_checksum].append(
                {
                    "image_id": str(img.id),
                    "benthicpqt_id": benthicpqt_id,
                    "collect_record_id": collect_record_id,
                    "original_image_name": img.original_image_name,
                    "original_image_checksum": img.original_image_checksum,
                }
            )

        duplicates = defaultdict(list)
        for cr_image in cr_images:
            dups = duplicates_by_checksum.get(cr_image.original_image_checksum, [])
            for dup in dups:
                cr_image_id = str(cr_image.id)
                if dup["image_id"] != cr_image_id:
                    duplicates[cr_image_id].append(dup)

        if not duplicates:
            return OK

        return WARN, self.DUPLICATE_IMAGES, {"duplicates": duplicates}


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

            if anno.is_confirmed:
                images[image_id][uid]["image_id"] = image_id
                images[image_id][uid]["confirmed"] += 1
                images[image_id][uid]["attribute"] = anno.benthic_attribute.id
                images[image_id][uid]["growth_form"] = (
                    anno.growth_form.id if anno.growth_form else ""
                )
                points.add(point_id)
            elif point_id not in points:
                images[image_id][uid]["image_id"] = image_id
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

                if values["confirmed"] > 0:
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
