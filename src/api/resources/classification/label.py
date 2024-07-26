from rest_framework import serializers

from ...models import LabelMapping
from ...permissions import UnauthenticatedReadOnlyPermission
from ..base import BaseAPIFilterSet, BaseAPISerializer, BaseApiViewSet


class LabelMappingSerializer(BaseAPISerializer):
    updated_by = None
    label_id = serializers.ReadOnlyField(source="label.pk")
    label_name = serializers.ReadOnlyField(source="label.name")
    ba_id = serializers.ReadOnlyField(source="label.benthic_attribute.pk")
    ba_name = serializers.ReadOnlyField(source="label.benthic_attribute.name")
    gf_id = serializers.SerializerMethodField()
    gf_name = serializers.SerializerMethodField()

    def get_gf_id(self, obj):
        return obj.label.growth_form.pk if obj.label.growth_form else None

    def get_gf_name(self, obj):
        return obj.label.growth_form.name if obj.label.growth_form else None

    class Meta:
        model = LabelMapping
        exclude = ["created_on", "created_by", "updated_on", "updated_by", "label"]


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
        return LabelMapping.objects.select_related(
            "label", "label__benthic_attribute", "label__growth_form"
        )
