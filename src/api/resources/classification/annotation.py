from rest_framework import serializers

from ...models import Annotation
from ..base import BaseAPISerializer


class AnnotationSerializer(BaseAPISerializer):
    benthic_attribute = serializers.SerializerMethodField()
    growth_form = serializers.SerializerMethodField()

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

    def get_benthic_attribute(self, obj):
        return obj.benthic_attribute_id

    def get_growth_form(self, obj):
        return obj.growth_form_id
