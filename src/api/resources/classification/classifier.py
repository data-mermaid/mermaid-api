from django.utils.functional import cached_property
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.permissions import SAFE_METHODS
from rest_framework.response import Response

from ...models import BenthicAttributeGrowthForm, Classifier
from ...models.classification import ClassifierNotConfiguredError
from ...permissions import UnauthenticatedReadOnlyPermission
from ..base import BaseAPIFilterSet, BaseAPISerializer, BaseApiViewSet


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
    is_default = serializers.SerializerMethodField()

    class Meta:
        model = Classifier
        fields = [
            "id",
            "name",
            "version",
            "classifier_type",
            "config",
            "description",
            "benthic_attribute_growth_forms",
            "is_default",
            "created_on",
            "created_by",
            "updated_on",
            "updated_by",
        ]

    @cached_property
    def _active_pk(self):
        # One child serializer instance serves every row in a list request,
        # so caching here bounds the lookup to one query per request
        # regardless of row count.
        try:
            return Classifier.active().pk
        except ClassifierNotConfiguredError:
            return None

    def get_is_default(self, obj):
        return obj.pk == self._active_pk


class ClassifierFilterSet(BaseAPIFilterSet):
    class Meta:
        model = Classifier
        fields = ["version"]


class ClassifierViewSet(BaseApiViewSet):
    serializer_class = ClassifierSerializer
    permission_classes = (UnauthenticatedReadOnlyPermission,)
    method_authentication_classes = {"GET": []}
    filterset_class = ClassifierFilterSet

    def get_queryset(self):
        return Classifier.objects.prefetch_related("benthic_attribute_growth_forms").order_by(
            "-created_on"
        )

    @action(detail=False, methods=SAFE_METHODS)
    def latest(self, request, *args, **kwargs):
        try:
            classifier = Classifier.active()
        except ClassifierNotConfiguredError as err:
            raise NotFound("No active classifier configured") from err

        serializer = ClassifierSerializer(instance=classifier)
        return Response(serializer.data)
