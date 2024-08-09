from django.db.models import Q
from rest_condition import And
from rest_framework import permissions, serializers, status
from rest_framework.exceptions import MethodNotAllowed
from rest_framework.response import Response

from ...exceptions import check_uuid
from ...models import (
    BENTHICPQT_PROTOCOL,
    ClassificationStatus,
    CollectRecord,
    Image,
    ObsBenthicPhotoQuadrat,
    ProjectProfile,
)
from ...utils import truthy
from ...utils.classification import classify_image_job, create_classification_status
from ..base import BaseAPISerializer, BaseProjectApiViewSet
from .classification_status import ClassificationStatusSerializer
from .point import PointSerializer


class ImagePermission(permissions.BasePermission):
    def has_permission(self, request, view):
        profile = getattr(request.user, "profile")
        if profile is None:
            return False

        project_id = view.kwargs["project_pk"]
        image_id = view.kwargs.get("pk")

        cr_ids = CollectRecord.objects.filter(profile=profile, project_id=project_id).values_list(
            "id", flat=True
        )

        if request.method in ("PATCH", "PUT", "DELETE"):
            if image_id is None:
                return False

            return Image.objects.filter(id=image_id, collect_record_id__in=cr_ids).exists()
        elif request.method == "POST":
            collect_record_id = request.data.get("collect_record_id")
            return CollectRecord.objects.filter(id=collect_record_id, profile=profile).exists()
        else:
            return ProjectProfile.objects.filter(profile=profile, project_id=project_id).exists()


class ImageSerializer(BaseAPISerializer):
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


class ImageViewSet(BaseProjectApiViewSet):
    queryset = Image.objects.all()
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

    def partial_update(self, request, pk=None):
        raise MethodNotAllowed("PATCH")

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
            classify_image_job(image_record.pk)

        data = ImageSerializer(instance=image_record).data
        return Response(data=data, status=status.HTTP_201_CREATED)

    def update(self, request, pk, *args, **kwargs):
        raise NotImplementedError()
        # data = request.data
        # qs = self.limit_to_project(request, pk, *args, **kwargs)
        # image_record = qs.get(id=pk)

        # if "classification_status" in data:
        #     data.pop("classification_status")

        # if "points" in data:
        #     points_data = data.pop("points")

        # return Response()
