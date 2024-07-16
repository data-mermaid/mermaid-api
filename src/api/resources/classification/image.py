from django.db.models import Q
from rest_condition import And
from rest_framework import status
from rest_framework.response import Response

from ...exceptions import check_uuid
from ...models import BENTHICPQT_PROTOCOL, CollectRecord, Image, ObsBenthicPhotoQuadrat
from ...permissions import CollectRecordOwner
from ...utils import truthy
from ...utils.classification import classify_image
from ..base import BaseAPISerializer, BaseProjectApiViewSet


class ImageSerializer(BaseAPISerializer):
    class Meta:
        model = Image
        exclude = ["original_image_checksum"]


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
            | Q(**{f"observation__{ObsBenthicPhotoQuadrat.project_lookup}": project_pk})
        )

    @classmethod
    def get_extra_actions(cls):
        extra_actions = super().get_extra_actions()
        filtered_actions = [
            action for action in extra_actions if action.url_name not in ["missing", "updates"]
        ]
        return filtered_actions

    def create(self, request, *args, **kwargs):
        image = request.data.get("image")
        collect_record_id = request.data.get("collect_record_id")
        trigger_classification = truthy(request.data.get("classify", False))

        collect_record = CollectRecord.objects.get(pk=collect_record_id)
        if collect_record.protocol != BENTHICPQT_PROTOCOL:
            return Response(
                {"error": "Image upload is only allowed for Benthic Photo Quadrat sample units."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        img = Image.objects.create(collect_record_id=collect_record.pk, image=image)

        if trigger_classification:
            classify_image(img)

        # Add validation to ensure that image collect record is a photo quadrat
        data = ImageSerializer(instance=img).data
        return Response(data=data, status=status.HTTP_201_CREATED)
