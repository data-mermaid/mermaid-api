import sys
from django.db.models import Q
from rest_condition import And
from rest_framework import serializers, status
from rest_framework.response import Response

from ...exceptions import check_uuid
from ...models import BENTHICPQT_PROTOCOL, ClassificationStatus, CollectRecord, Image, ObsBenthicPhotoQuadrat
from ...permissions import CollectRecordOwner
from ...utils import truthy
from ...utils.classification import classify_image_job, create_classification_status
from ..base import BaseAPISerializer, BaseProjectApiViewSet
from .image_classification import ClassificationStatusSerializer


class ImageSerializer(BaseAPISerializer):
    classification_status = serializers.SerializerMethodField()

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
    permission_classes = [And(BaseProjectApiViewSet.permission_classes[0], CollectRecordOwner)]

    def limit_to_project(self, request, *args, **kwargs):
        qs = self.get_queryset()
        project_pk = check_uuid(kwargs["project_pk"])
        cr_ids = CollectRecord.objects.filter(project_id=project_pk).values_list("id", flat=True)
        return qs.filter(
            Q(collect_record_id__in=cr_ids)
            | Q(**{f"obs_benthic_photo_quadrats__{ObsBenthicPhotoQuadrat.project_lookup}": project_pk})
        )

    @classmethod
    def get_extra_actions(cls):
        extra_actions = super().get_extra_actions()
        filtered_actions = [
            action for action in extra_actions if action.url_name not in ["missing", "updates"]
        ]
        return filtered_actions

    def create(self, request, *args, **kwargs):
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
            image_record = Image.objects.create(collect_record_id=collect_record.pk, image=image_file)
        except Exception as err:
            print(f"Create image record: {err}")
            return Response(data=None, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        if trigger_classification:
            create_classification_status(image_record, status=ClassificationStatus.PENDING)
            classify_image_job(image_record)

        data = ImageSerializer(instance=image_record).data
        return Response(data=data, status=status.HTTP_201_CREATED)
