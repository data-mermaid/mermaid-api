from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework import permissions, serializers, status
from rest_framework.exceptions import MethodNotAllowed, NotFound, ValidationError
from rest_framework.response import Response

from ...exceptions import check_uuid
from ...models import (
    BENTHICPQT_PROTOCOL,
    Annotation,
    ClassificationStatus,
    CollectRecord,
    Image,
    ObsBenthicPhotoQuadrat,
    Point,
    ProjectProfile,
)
from ...models.classification import get_image_bucket
from ...permissions import cached_lookup
from ...utils import truthy
from ...utils.classification import classify_image_job, create_classification_status
from ..base import (
    PROJECT_DATA_PERMISSION,
    BaseAPIFilterSet,
    BaseAPISerializer,
    BaseProjectApiViewSet,
)
from ..mixins import DynamicFieldsMixin
from .annotation import SaveAnnotationSerializer
from .classification_status import ClassificationStatusSerializer
from .point import PointSerializer

IMAGE_PERMISSION_CACHE_ATTR = "_image_permission_cache"


class ImagePermission(permissions.BasePermission):
    def has_permission(self, request, view):
        profile = getattr(request.user, "profile", None)
        if profile is None:
            return False

        project_id = view.kwargs["project_pk"]
        image_id = view.kwargs.get("pk")

        if request.method == "PUT":
            return False

        def _load():
            if request.method in ("PATCH", "DELETE"):
                if image_id is None:
                    return False
                cr_ids = CollectRecord.objects.filter(
                    profile=profile, project_id=project_id
                ).values_list("id", flat=True)
                return Image.objects.filter(id=image_id, collect_record_id__in=cr_ids).exists()
            elif request.method == "POST":
                collect_record_id = request.data.get("collect_record_id")
                return CollectRecord.objects.filter(id=collect_record_id, profile=profile).exists()
            else:
                return ProjectProfile.objects.filter(
                    profile=profile, project_id=project_id
                ).exists()

        # PATCH/DELETE/GET (has_permission) is re-checked by DRF's OR.has_object_permission
        # (see BaseProjectApiViewSet.permission_classes) on every detail-level request, so
        # memoize per-request the same way api.permissions.cached_lookup does for
        # get_project/get_project_profile - otherwise a non-project-member's image access
        # (the whole reason this permission exists) re-runs these queries a second time.
        cache_key = (
            request.method,
            project_id,
            image_id,
            request.data.get("collect_record_id") if request.method == "POST" else None,
            str(profile.pk),
        )
        return cached_lookup(request, IMAGE_PERMISSION_CACHE_ATTR, cache_key, _load)


class ImageSerializer(DynamicFieldsMixin, BaseAPISerializer):
    classification_status = serializers.SerializerMethodField()
    patch_size = serializers.SerializerMethodField()
    num_confirmed = serializers.SerializerMethodField()
    num_unconfirmed = serializers.SerializerMethodField()
    num_unclassified = serializers.SerializerMethodField()
    points = PointSerializer(many=True)

    class Meta:
        model = Image
        additional_fields = ["classification_status"]
        exclude = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._counts_cache = {}

    def get_classification_status(self, obj):
        statuses = obj.statuses.all()
        latest = max(statuses, key=lambda s: s.created_on, default=None)
        if latest:
            return ClassificationStatusSerializer(latest).data
        return None

    def get_patch_size(self, obj):
        # All machine annotations on an image share one classifier, so the
        # first one found is authoritative.
        for point in obj.points.all():
            for annotation in point.annotations.all():
                if annotation.classifier_id is not None:
                    return annotation.classifier.patch_size
        return None

    def _summarize_counts(self, obj):
        if obj.pk in self._counts_cache:
            return self._counts_cache[obj.pk]

        count_confirmed = 0
        count_unconfirmed = 0
        count_unclassified = 0
        for point in obj.points.all():
            annotations = list(point.annotations.all())
            if annotations:
                if any(annotation.is_confirmed for annotation in annotations):
                    count_confirmed += 1
                else:
                    count_unconfirmed += 1
            else:
                count_unclassified += 1

        result = (count_confirmed, count_unconfirmed, count_unclassified)
        self._counts_cache[obj.pk] = result
        return result

    def get_num_confirmed(self, obj):
        count_confirmed, _, _ = self._summarize_counts(obj)
        return count_confirmed

    def get_num_unconfirmed(self, obj):
        _, count_unconfirmed, _ = self._summarize_counts(obj)
        return count_unconfirmed

    def get_num_unclassified(self, obj):
        _, _, count_unclassified = self._summarize_counts(obj)
        return count_unclassified


class PatchImageSerializer(BaseAPISerializer):
    class Meta:
        model = Image
        fields = ["id", "points"]
        read_only_fields = ["id", "points"]

    def check_image_points_relationship(self, data):
        image_id = data.get("id")
        points = data.get("points") or []
        point_ids = [pnt.get("id") for pnt in points if "id" in pnt]
        num_point_instances = Point.objects.filter(id__in=point_ids, image_id=image_id).count()
        if len(point_ids) != num_point_instances:
            raise ValidationError("Point does not belong to image")

    def validate(self, data):
        self.check_image_points_relationship(data)
        return super().validate(data)


class ImageFilterSet(BaseAPIFilterSet):
    class Meta:
        model = Image
        fields = [
            "collect_record_id",
        ]


class ImageViewSet(BaseProjectApiViewSet):
    queryset = (
        Image.objects.prefetch_related(
            "points",
            "points__annotations",
            "points__annotations__classifier",
            "statuses",
        )
        .all()
        .order_by("created_on")
    )

    serializer_class = ImageSerializer
    permission_classes = [PROJECT_DATA_PERMISSION | ImagePermission]
    filterset_class = ImageFilterSet

    def perform_destroy(self, instance):
        # Lock the row so this serializes against create_classification_status(),
        # which also locks via select_for_update(). Without this, the async
        # classification worker can insert a new ClassificationStatus between
        # Django's delete-collector query and the final DELETE, causing an
        # IntegrityError on the class_status FK.
        with transaction.atomic():
            try:
                locked_instance = Image.objects.select_for_update().get(pk=instance.pk)
            except Image.DoesNotExist:
                raise NotFound()
            locked_instance.delete()

    def limit_to_project(self, request, *args, **kwargs):
        qs = self.get_queryset()
        profile = getattr(request.user, "profile", None)
        if profile is None:
            return qs.none()

        project_pk = check_uuid(kwargs["project_pk"])
        cr_ids = CollectRecord.objects.filter(project_id=project_pk, profile=profile).values_list(
            "id", flat=True
        )
        self.queryset = qs.filter(
            Q(collect_record_id__in=cr_ids)
            | Q(
                **{
                    f"obs_benthic_photo_quadrats__{ObsBenthicPhotoQuadrat.project_lookup}": project_pk
                }
            )
        ).distinct()
        return self.queryset

    @classmethod
    def get_extra_actions(cls):
        extra_actions = super().get_extra_actions()
        filtered_actions = [
            action for action in extra_actions if action.url_name not in ["missing", "updates"]
        ]
        return filtered_actions

    def update(self, request, pk=None, **kwargs):
        raise MethodNotAllowed("PUT")

    def create(self, request, *args, **kwargs):
        profile = request.user.profile
        image_file = request.data.get("image")
        collect_record_id = request.data.get("collect_record_id")
        trigger_classification = truthy(request.data.get("classify", True))

        if image_file and image_file.size > settings.MAX_IMAGE_FILE_SIZE:
            mb = settings.MAX_IMAGE_FILE_SIZE // (1024 * 1024)
            return Response(
                {"error": f"Image exceeds the {mb} MB size limit."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        collect_record = CollectRecord.objects.get_or_none(pk=collect_record_id)
        if collect_record is None:
            return Response(
                {"error": f"[{collect_record_id}] Collect record does not exist."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if collect_record.protocol != BENTHICPQT_PROTOCOL:
            return Response(
                {
                    "error": f"[{collect_record.protocol}] Image upload is only allowed for Benthic Photo Quadrat sample units."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        elif collect_record.data.get("image_classification") is not True:
            return Response(
                {
                    "error": "Benthic Photo Quadrat sample unit not flagged for image classification."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            project = collect_record.project
            bucket = get_image_bucket(project)

            image_record = Image.objects.create(
                collect_record_id=collect_record.pk,
                image=image_file,
                image_bucket=bucket,
                created_by=profile,
                updated_by=profile,
            )
        except Exception as err:
            if hasattr(err, "message"):
                msg = err.message
            else:
                msg = str(err)
            return Response(data={"detail": msg}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        if trigger_classification:
            create_classification_status(image_record, status=ClassificationStatus.PENDING)
            # num_points is left unset here; classify_image_job falls back to the
            # deployment-wide point count in effect when the job runs.
            classify_image_job(image_record.pk)

        data = ImageSerializer(instance=image_record, context={"request": request}).data
        return Response(data=data, status=status.HTTP_201_CREATED)

    def _get_validated_annotations(self, point_data, points_by_id):
        if not isinstance(point_data.get("annotations"), list):
            raise ValidationError("'annotations' is required.")

        point_id = point_data.get("id")
        point = points_by_id.get(str(point_id))
        if point is None:
            raise ValidationError(f"Point ({point_id}) is missing")

        return point, point_data.get("annotations")

    def _check_only_one_confirmed_annotation(self, annotations):
        confirmed_count = sum(1 for anno in annotations if anno.get("is_confirmed"))
        if confirmed_count > 1:
            raise ValidationError("Only one annotation can be confirmed.")

    def _delete_stale_user_annotations(self, points, point_ids, annotations_by_id):
        # Keep a submitted user annotation only if it belongs to the point it was
        # submitted under; other user annotations on the submitted points are deleted.
        keep_ids = []
        for point_data in points:
            for anno in point_data.get("annotations") or []:
                if anno.get("is_machine_created"):
                    continue
                instance = annotations_by_id.get(str(anno.get("id")))
                if instance is not None and str(instance.point_id) == str(point_data.get("id")):
                    keep_ids.append(instance.id)

        Annotation.objects.filter(point_id__in=point_ids, is_machine_created=False).exclude(
            id__in=keep_ids
        ).delete()

    def _machine_annotation_confirmed_change(self, instance, annotation_data):
        is_confirmed = serializers.BooleanField().run_validation(
            annotation_data.get("is_confirmed") or False
        )
        return is_confirmed if instance.is_confirmed != is_confirmed else None

    def _save_machine_annotation_confirmations(self, to_confirm_ids, to_unconfirm_ids):
        now = timezone.now()  # .update() skips auto_now
        if to_unconfirm_ids:
            Annotation.objects.filter(id__in=to_unconfirm_ids).update(
                is_confirmed=False, updated_on=now
            )
        if to_confirm_ids:
            Annotation.objects.filter(id__in=to_confirm_ids).update(
                is_confirmed=True, updated_on=now
            )

    def _is_user_annotation_unchanged(self, instance, annotation_data):
        is_confirmed = serializers.BooleanField().run_validation(
            annotation_data.get("is_confirmed") or False
        )
        growth_form = annotation_data.get("growth_form")
        return (
            str(instance.benthic_attribute_id) == str(annotation_data.get("benthic_attribute"))
            and (str(growth_form) if growth_form else None)
            == (str(instance.growth_form_id) if instance.growth_form_id else None)
            and instance.is_confirmed == is_confirmed
        )

    def partial_update(self, request, pk, *args, **kwargs):
        data = request.data
        qs = self.limit_to_project(request, pk, *args, **kwargs)
        image_record = qs.prefetch_related(None).get(id=pk)

        if "points" not in data:
            raise ValidationError("'points' is required.")

        context = {"request": request}
        with transaction.atomic():
            points = data.get("points")
            serializer = PatchImageSerializer(data=data, instance=image_record, context=context)
            serializer.is_valid(raise_exception=True)

            point_ids = [pnt.get("id") for pnt in points if pnt.get("id")]
            points_by_id = {
                str(pid): pnt
                for pid, pnt in Point.objects.filter(image_id=pk, id__in=point_ids)
                .in_bulk()
                .items()
            }
            annotations_by_id = {
                str(anno.id): anno for anno in Annotation.objects.filter(point_id__in=point_ids)
            }
            self._delete_stale_user_annotations(points, point_ids, annotations_by_id)

            to_confirm_ids = []
            to_unconfirm_ids = []

            for point_data in points:
                point, annotations = self._get_validated_annotations(point_data, points_by_id)
                self._check_only_one_confirmed_annotation(annotations)

                for annotation_data in annotations:
                    anno_instance = annotations_by_id.get(str(annotation_data.get("id")))
                    if anno_instance is not None and anno_instance.point_id != point.id:
                        anno_instance = None

                    if anno_instance is not None and anno_instance.is_machine_created:
                        new_confirmed = self._machine_annotation_confirmed_change(
                            anno_instance, annotation_data
                        )
                        if new_confirmed is not None:
                            (to_confirm_ids if new_confirmed else to_unconfirm_ids).append(
                                anno_instance.id
                            )
                        continue

                    if anno_instance is not None and self._is_user_annotation_unchanged(
                        anno_instance, annotation_data
                    ):
                        continue

                    anno_serializer = SaveAnnotationSerializer(
                        instance=anno_instance, data=annotation_data, context=context
                    )
                    anno_serializer.is_valid(raise_exception=True)
                    anno_serializer.save(point=point)

            self._save_machine_annotation_confirmations(to_confirm_ids, to_unconfirm_ids)

        updated_image_record = qs.get(id=pk)
        return Response(ImageSerializer(instance=updated_image_record).data)
