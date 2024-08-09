from ...models import Point
from ..base import BaseAPISerializer
from .annotation import AnnotationSerializer


class PointSerializer(BaseAPISerializer):
    annotations = AnnotationSerializer(many=True)

    class Meta:
        model = Point
        fields = ["id", "image", "row", "column", "annotations"]
