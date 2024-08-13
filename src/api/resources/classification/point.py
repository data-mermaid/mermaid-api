from rest_framework.exceptions import ValidationError

from ...models import Annotation, Point
from ..base import BaseAPISerializer
from .annotation import (
    AnnotationSerializer,
    SaveAnnotationSerializer,
    # UserAnnotationSerializer,
)


class PointSerializer(BaseAPISerializer):
    annotations = AnnotationSerializer(many=True)

    class Meta:
        model = Point
        fields = ["id", "image", "row", "column", "annotations"]


class SavePointSerializer(BaseAPISerializer):
    annotations = SaveAnnotationSerializer(many=True)

    class Meta:
        model = Point
        fields = ["id", "image", "annotations"]
        read_only_fields = ["id", "image"]
    
    def check_only_one_is_confirmed(self, data):
        annotation_data = data.get("annotations") or []
        if len([anno for anno in annotation_data if anno.get("is_confirmed")]) > 1:
            raise ValidationError("Only one annotation can be confirmed.")

    def validate(self, data):
        self.check_only_one_is_confirmed(data)
        return super().validate(data)

    # def update(self, instance, validated_data):
    #     validated_data = self.validated_data

    #     # Delete user annotations that have been removed
    #     # from "annotations" list (i.e. are "deleted").
    #     if instance is not None:
    #         user_annotation_ids = [
    #             anno.get("id")
    #             for anno in (validated_data.get("annotations") or [])
    #             if not anno.get("classifier") and anno.get("id")
    #         ]
    #         Annotation.objects.filter(point=instance, classifier=None).exclude(
    #             id__in=user_annotation_ids
    #         ).delete()

    #     # for annotation in validated_data.get("annotations") or []:
    #     #     if annotation.get("classifier"):
    #     #         serializer = MachineAnnotationSerializer(data=annotation)
    #     #     else:
    #             # serializer = UserAnnotationSerializer(data=annotation)
    #     #     serializer.is_valid(raise_exception=True)
    #     #     serializer.save()
        
    #     return super().update(instance, validated_data)
