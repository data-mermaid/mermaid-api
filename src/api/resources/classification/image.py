from typing import Any, Dict, List


from django.conf import settings
from django.db.models import Q
from django.db import transaction
from rest_condition import And
from rest_framework import permissions, serializers, status
from rest_framework.exceptions import MethodNotAllowed, ValidationError
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
    Profile,
    ProjectProfile,
)
from ...utils import truthy
from ...utils.classification import classify_image, classify_image_job, create_classification_status
from ..base import BaseAPISerializer, BaseProjectApiViewSet
from ..mixins import DynamicFieldsMixin
from .annotation import SaveAnnotationSerializer
from .classification_status import ClassificationStatusSerializer
from .point import SavePointSerializer, PointSerializer


class ImagePermission(permissions.BasePermission):
    def has_permission(self, request, view):
        profile = getattr(request.user, "profile")
        if profile is None:
            return False

        project_id = view.kwargs["project_pk"]
        image_id = view.kwargs.get("pk")

        if request.method == "PUT":
            return False
        elif request.method in ("PATCH", "DELETE"):
            if image_id is None:
                return False
            cr_ids = CollectRecord.objects.filter(profile=profile, project_id=project_id).values_list(
                "id", flat=True
            )
            return Image.objects.filter(id=image_id, collect_record_id__in=cr_ids).exists()
        elif request.method == "POST":
            collect_record_id = request.data.get("collect_record_id")
            return CollectRecord.objects.filter(id=collect_record_id, profile=profile).exists()
        else:
            return ProjectProfile.objects.filter(profile=profile, project_id=project_id).exists()


class ImageSerializer(DynamicFieldsMixin, BaseAPISerializer):
    classification_status = serializers.SerializerMethodField()
    points = PointSerializer(many=True)

    class Meta:
        model = Image
        additional_fields = ["classification_status"]
        exclude = ["original_image_checksum"]

    def get_classification_status(self, obj):
        latest_status = obj.statuses.order_by("-created_on").first()
        if latest_status:
            return ClassificationStatusSerializer(latest_status).data
        return None


class PatchImageSerializer(BaseAPISerializer):
    # points = SavePointSerializer(many=True)

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

    # def update(self, instance, validated_data):
    #     print(f"validated_data: {validated_data}")
    #     for point_data in validated_data.get("points"):
    #         serializer = SavePointSerializer(data=point_data, context=self.context)

    #         serializer.is_valid(raise_exception=True)
    #         point = Point.objects.get(id=point_data.get("id"))
    #         serializer.update(instance=point, validated_data=serializer.validated_data)
        
    #     return instance



class ImageViewSet(BaseProjectApiViewSet):
    queryset = Image.objects.prefetch_related("points", "points__annotations").all()
    serializer_class = ImageSerializer
    permission_classes = [And(BaseProjectApiViewSet.permission_classes[0], ImagePermission)]

    def limit_to_project(self, request, *args, **kwargs):
        qs = self.get_queryset()
        profile = getattr(request.user, "profile")
        if profile is None:
            return qs.none()

        project_pk = check_uuid(kwargs["project_pk"])
        cr_ids = CollectRecord.objects.filter(project_id=project_pk, profile=profile).values_list(
            "id", flat=True
        )
        return qs.filter(
            Q(collect_record_id__in=cr_ids)
            | Q(
                **{
                    f"obs_benthic_photo_quadrats__{ObsBenthicPhotoQuadrat.project_lookup}": project_pk
                }
            )
        )

    @classmethod
    def get_extra_actions(cls):
        extra_actions = super().get_extra_actions()
        filtered_actions = [
            action for action in extra_actions if action.url_name not in ["missing", "updates"]
        ]
        return filtered_actions

    def update(self, request, pk=None):
        raise MethodNotAllowed("PUT")

    def create(self, request, *args, **kwargs):
        profile = request.user.profile
        image_file = request.data.get("image")
        collect_record_id = request.data.get("collect_record_id")
        trigger_classification = truthy(request.data.get("classify", True))

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

        try:
            image_record = Image.objects.create(
                collect_record_id=collect_record.pk,
                image=image_file,
                created_by=profile,
                updated_by=profile,
            )
        except Exception as err:
            print(f"Create image record: {err}")
            return Response(data=None, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        if trigger_classification:
            create_classification_status(image_record, status=ClassificationStatus.PENDING)
            if settings.ENVIRONMENT == "local":
                classify_image(image_record.pk)
            else:
                classify_image_job(image_record.pk)

        data = ImageSerializer(instance=image_record).data
        return Response(data=data, status=status.HTTP_201_CREATED)


    def partial_update(self, request, pk, *args, **kwargs):
        data = request.data
        qs = self.limit_to_project(request, pk, *args, **kwargs)
        image_record = qs.get(id=pk)

        if "points" not in data:
            raise ValidationError("'points' is required.")

        context = {"request": request}
        with transaction.atomic():
            points = data.get("points")
            serializer = PatchImageSerializer(data=data, instance=image_record, context=context)
            serializer.is_valid(raise_exception=True)

            for point_data in points:
                if "annotations" not in point_data:
                    raise ValidationError("'annotations' is required.")
                
                point_id = point_data.get("id")
                point = Point.objects.get_or_none(id=point_data.get("id"), image=pk)
                if point is None:
                    raise ValidationError(f"Point ({point_id}) is missing")

                annotations = point_data.get("annotations")

                user_annotation_ids = [
                    anno.get("id")
                    for anno in annotations
                    if not anno.get("is_machine_created") and anno.get("id")
                ]
                Annotation.objects.filter(point=point, is_machine_created=False).exclude(
                    id__in=user_annotation_ids
                ).delete()

                pnt_serializer = SavePointSerializer(instance=point, data=point_data, context=context)
                pnt_serializer.is_valid(raise_exception=True)

                for annotation_data in annotations:
                    anno_id = annotation_data.get("id")
                    anno_instance = Annotation.objects.get_or_none(id=anno_id, point=point)
                    anno_serializer = SaveAnnotationSerializer(
                        instance=anno_instance,
                        data=annotation_data,
                        context=context
                    )
                    anno_serializer.is_valid(raise_exception=True)
                    anno_serializer.save(point=point)

        updated_image_record = qs.get(id=pk)
        return Response(ImageSerializer(instance=updated_image_record).data)
