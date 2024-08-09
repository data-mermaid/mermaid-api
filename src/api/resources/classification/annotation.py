from ...models import Annotation
from ..base import BaseAPISerializer


class AnnotationSerializer(BaseAPISerializer):
    class Meta:
        model = Annotation
        fields = [
            "id",
            "point",
            "benthic_attribute",
            "growth_form",
            "classifier",
            "score",
            "is_confirmed",
        ]
