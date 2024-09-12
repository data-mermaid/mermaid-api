from rest_framework import serializers

from ...models import LabelMapping
from ...permissions import UnauthenticatedReadOnlyPermission
from ..base import BaseAPIFilterSet, BaseAPISerializer, BaseApiViewSet


class LabelMappingSerializer(BaseAPISerializer):
    updated_by = None
    benthic_attribute_id = serializers.ReadOnlyField(source="benthic_attribute.pk")
    benthic_attribute_name = serializers.ReadOnlyField(source="benthic_attribute.name")
    growth_form_id = serializers.SerializerMethodField()
    growth_form_name = serializers.SerializerMethodField()

    def get_growth_form_id(self, obj):
        return obj.growth_form.pk if obj.growth_form else None

    def get_growth_form_name(self, obj):
        return obj.growth_form.name if obj.growth_form else None

    class Meta:
        model = LabelMapping
        exclude = ["created_on", "created_by", "updated_on", "updated_by"]


class LabelMappingFilterSet(BaseAPIFilterSet):
    class Meta:
        model = LabelMapping
        fields = "__all__"


# TODO: add csv route
class LabelMappingViewSet(BaseApiViewSet):
    serializer_class = LabelMappingSerializer
    # TODO: perms/workflow for add/edit/delete
    permission_classes = [UnauthenticatedReadOnlyPermission]
    method_authentication_classes = {"GET": []}
    filterset_class = LabelMappingFilterSet

    def get_queryset(self):
        return LabelMapping.objects.select_related("benthic_attribute", "growth_form")
