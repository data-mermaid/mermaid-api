from rest_framework.exceptions import ValidationError

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
            "is_machine_created",
        ]


class SaveAnnotationSerializer(BaseAPISerializer):
    class Meta:
        model = Annotation
        fields = "__all__"
        read_only_field = ["is_machine_created"]

    def create(self, validated_data):
        if not validated_data.get("is_machine_created"):
            profile = self.context["request"].user.profile
            return Annotation.objects.create(
                point=validated_data["point"],
                benthic_attribute=validated_data["benthic_attribute"],
                growth_form=validated_data.get("growth_form"),
                is_confirmed=validated_data["is_confirmed"],
                score=100,
                classifier=None,
                created_by=profile,
                updated_by=profile,
            )
        else:
            raise ValidationError("Machine generated annotations can not be created.")

    def update(self, instance, validated_data):
        # User defined
        if not instance.is_machine_created:
            profile = self.context["request"].user.profile
            instance.benthic_attribute = validated_data["benthic_attribute"]
            instance.growth_form = validated_data.get("growth_form")
            instance.is_confirmed = validated_data["is_confirmed"]
            instance.score = 100
            instance.classifier = None
            instance.updated_by = profile
            instance.save()

        # Machine defined
        else:
            validated_data = self.validated_data
            instance.is_confirmed = validated_data.get("is_confirmed") or False
            instance.save()

        return instance
