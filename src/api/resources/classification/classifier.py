from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.permissions import SAFE_METHODS
from rest_framework.response import Response

from ...models import BenthicAttributeGrowthForm, Classifier
from ...permissions import UnauthenticatedReadOnlyPermission
from ..base import BaseAPISerializer, BaseApiViewSet


class BenthicAttributeGrowthFormSerializer(BaseAPISerializer):
    benthic_attribute_name = serializers.ReadOnlyField(source="benthic_attribute.name")
    growth_form_name = serializers.SerializerMethodField()

    def get_growth_form_name(self, obj):
        return obj.growth_form.name if obj.growth_form else None

    class Meta:
        model = BenthicAttributeGrowthForm
        fields = ["benthic_attribute_name", "growth_form_name"]


class ClassifierSerializer(BaseAPISerializer):
    benthic_attribute_growth_forms = BenthicAttributeGrowthFormSerializer(many=True)

    class Meta:
        model = Classifier
        exclude = []


class ClassifierViewSet(BaseApiViewSet):
    serializer_class = ClassifierSerializer
    permission_classes = (UnauthenticatedReadOnlyPermission,)
    method_authentication_classes = {"GET": []}

    def get_queryset(self):
        return Classifier.objects.prefetch_related("benthic_attribute_growth_forms").all()

    @action(detail=False, methods=SAFE_METHODS)
    def latest(self, request, *args, **kwargs):
        classifier = self.get_queryset().order_by("-created_on").first()
        if not classifier:
            raise NotFound("No classifiers found")

        serializer = ClassifierSerializer(instance=classifier)
        return Response(serializer.data)
