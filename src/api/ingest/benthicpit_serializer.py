from rest_framework import serializers

from ..models import BenthicAttribute, GrowthForm, ReefSlope
from .serializers import CollectRecordCSVSerializer, build_choices
from ..fields import LazyChoiceField


__all__ = ["BenthicPITCSVSerializer"]


def growth_form_choices():
    return build_choices(GrowthForm.objects.choices(order_by="name"))


def reef_slopes_choices():
    return build_choices(ReefSlope.objects.choices(order_by="val"), "val")


def benthic_attributes_choices():
    print("benthic_attributes_choices")
    return [
        (str(c.id), str(c.name))
        for c in BenthicAttribute.objects.all().order_by("name")
    ]


class BenthicPITCSVSerializer(CollectRecordCSVSerializer):
    protocol = "benthicpit"
    observations_field = "data__obs_benthic_pits"
    ordering_field = "data__obs_benthic_pits__interval"
    additional_group_fields = CollectRecordCSVSerializer.additional_group_fields.copy()
    additional_group_fields.append("data__benthic_transect__label")

    header_map = CollectRecordCSVSerializer.header_map.copy()
    header_map.update(
        {
            "Interval size *": "data__interval_size",
            "Transect length surveyed *": "data__benthic_transect__len_surveyed",
            "Transect number *": "data__benthic_transect__number",
            "Transect label": "data__benthic_transect__label",
            "Reef Slope": "data__benthic_transect__reef_slope",
            "Benthic attribute *": "data__obs_benthic_pits__attribute",
            "Growth form *": "data__obs_benthic_pits__growth_form",
        }
    )

    data__interval_size = serializers.DecimalField(max_digits=4, decimal_places=2)
    data__benthic_transect__len_surveyed = serializers.IntegerField(min_value=0)
    data__benthic_transect__number = serializers.IntegerField(min_value=0)
    data__benthic_transect__label = serializers.CharField(
        allow_blank=True, required=False
    )
    data__benthic_transect__reef_slope = LazyChoiceField(
        choices=reef_slopes_choices, required=False, allow_null=True, allow_blank=True
    )

    data__obs_benthic_pits__interval = serializers.DecimalField(
        max_digits=7, decimal_places=2
    )
    data__obs_benthic_pits__attribute = LazyChoiceField(
        choices=benthic_attributes_choices
    )
    data__obs_benthic_pits__growth_form = LazyChoiceField(
        choices=growth_form_choices, required=False, allow_null=True, allow_blank=True
    )

    def validate(self, data):
        data = super().validate(data)
        return data
