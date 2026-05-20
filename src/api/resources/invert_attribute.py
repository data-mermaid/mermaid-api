from rest_framework import serializers

from ..models import InvertAttribute
from .base import BaseAPIFilterSet, BaseAPISerializer, BaseAttributeApiViewSet
from .mixins import CreateOrUpdateSerializerMixin


class InvertAttributeSerializer(CreateOrUpdateSerializerMixin, BaseAPISerializer):
    status = serializers.ReadOnlyField()
    taxonomic_rank = serializers.ReadOnlyField()
    name = serializers.SerializerMethodField()
    max_length = serializers.SerializerMethodField()
    parent = serializers.SerializerMethodField()
    group_of_interest = serializers.SerializerMethodField()
    max_length_type = serializers.SerializerMethodField()
    max_length_source = serializers.SerializerMethodField()
    max_length_url = serializers.SerializerMethodField()
    notes = serializers.SerializerMethodField()

    class Meta:
        model = InvertAttribute
        exclude = []

    def get_name(self, obj):
        return str(obj)

    def _taxon(self, obj):
        for attr in (
            "invertspecies",
            "invertgenus",
            "invertfamily",
            "invertorder",
            "invertclass",
        ):
            taxon = getattr(obj, attr, None)
            if taxon is not None:
                return taxon
        return None

    def get_max_length(self, obj):
        taxon = self._taxon(obj)
        return taxon.max_length if taxon is not None else None

    def get_parent(self, obj):
        species = getattr(obj, "invertspecies", None)
        if species is not None:
            return species.genus_id
        genus = getattr(obj, "invertgenus", None)
        if genus is not None:
            return genus.family_id
        family = getattr(obj, "invertfamily", None)
        if family is not None:
            return family.order_id
        order = getattr(obj, "invertorder", None)
        if order is not None:
            return order.invert_class_id
        return None

    def get_group_of_interest(self, obj):
        goi = getattr(obj, "invertgroupofinterest", None)
        if goi is not None:
            return obj.pk

        species = getattr(obj, "invertspecies", None)
        if species is not None:
            return species.genus.group_of_interest_id

        genus = getattr(obj, "invertgenus", None)
        if genus is not None:
            return genus.group_of_interest_id

        return None

    def get_max_length_type(self, obj):
        species = getattr(obj, "invertspecies", None)
        return species.max_length_type if species is not None else None

    def get_max_length_source(self, obj):
        species = getattr(obj, "invertspecies", None)
        return species.max_length_source if species is not None else None

    def get_max_length_url(self, obj):
        species = getattr(obj, "invertspecies", None)
        return species.max_length_url if species is not None else None

    def get_notes(self, obj):
        species = getattr(obj, "invertspecies", None)
        return species.notes if species is not None else None


class InvertAttributeFilterSet(BaseAPIFilterSet):
    class Meta:
        model = InvertAttribute
        fields = []


class InvertAttributeViewSet(BaseAttributeApiViewSet):
    serializer_class = InvertAttributeSerializer
    queryset = InvertAttribute.objects.select_related(
        "invertgroupofinterest",
        "invertclass",
        "invertorder__invert_class",
        "invertfamily__order__invert_class",
        "invertgenus__family__order__invert_class",
        "invertgenus__group_of_interest",
        "invertspecies__genus__family__order__invert_class",
        "invertspecies__genus__group_of_interest",
    ).order_by("id")
    filterset_class = InvertAttributeFilterSet
