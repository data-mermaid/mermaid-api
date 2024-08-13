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
    

    def check_only_one_is_confirmed(self, data):
        annotation_data = data.get("annotations") or []
        if len([anno for anno in annotation_data if anno.get("is_confirmed")]) > 1:
            raise ValidationError("Only one annotation can be confirmed.")

    def validate(self, data):
        self.check_only_one_is_confirmed(data)
        return super().validate(data)


# class SavePointSerializer(BaseAPISerializer):
#     annotations = SaveAnnotationSerializer(many=True)

#     class Meta:
#         model = Point
#         fields = ["id", "image", "annotations"]
#         read_only_fields = ["id", "image"]
    
#     def check_only_one_is_confirmed(self, data):
#         annotation_data = data.get("annotations") or []
#         if len([anno for anno in annotation_data if anno.get("is_confirmed")]) > 1:
#             raise ValidationError("Only one annotation can be confirmed.")

#     def validate(self, data):
#         self.check_only_one_is_confirmed(data)
#         return super().validate(data)
