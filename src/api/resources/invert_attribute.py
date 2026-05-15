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
    class_goi = serializers.SerializerMethodField()
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
            "invertclassgroupofinterest",
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
            return order.class_goi_id
        return None

    def get_class_goi(self, obj):
        species = getattr(obj, "invertspecies", None)
        if species is not None:
            return species.genus.family.order.class_goi_id
        genus = getattr(obj, "invertgenus", None)
        if genus is not None:
            return genus.family.order.class_goi_id
        family = getattr(obj, "invertfamily", None)
        if family is not None:
            return family.order.class_goi_id
        order = getattr(obj, "invertorder", None)
        if order is not None:
            return order.class_goi_id
        class_goi = getattr(obj, "invertclassgroupofinterest", None)
        if class_goi is not None:
            return class_goi.pk
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
    # Exclude internal InvertClass nodes — user-visible hierarchy is
    # ClassGroupOfInterest → Order → Family → Genus → Species.
    # select_related pre-fetches full chain to class_goi for the class_goi field.
    queryset = (
        InvertAttribute.objects.select_related(
            "invertclassgroupofinterest__invert_class",
            "invertclassgroupofinterest__group_of_interest",
            "invertorder__class_goi",
            "invertfamily__order__class_goi",
            "invertgenus__family__order__class_goi",
            "invertspecies__genus__family__order__class_goi",
        )
        .filter(invertclass__isnull=True)
        .order_by("id")
    )
    filterset_class = InvertAttributeFilterSet
