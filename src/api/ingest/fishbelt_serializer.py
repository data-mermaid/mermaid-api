from rest_framework import serializers

from ..fields import LazyChoiceField
from ..models import BeltTransectWidth, FishSizeBin, ReefSlope
from ..models.view_models import FishAttributeView
from .serializers import CollectRecordCSVSerializer, build_choices

__all__ = ["FishBeltCSVSerializer"]


def reef_slopes_choices():
    return build_choices(ReefSlope.objects.choices(order_by="val"), "val")


def belt_transect_widths_choices():
    return build_choices(BeltTransectWidth.objects.choices(order_by="val"), "val")


def fish_size_bins_choices():
    return build_choices(FishSizeBin.objects.choices(order_by="val"), "val")


def fish_attributes_choices():
    return [
        (str(c.id), str(c.name))
        for c in FishAttributeView.objects.all().order_by("name")
    ]


class FishBeltCSVSerializer(CollectRecordCSVSerializer):
    protocol = "fishbelt"
    observations_fields = ["data__obs_belt_fishes"]
    additional_group_fields = CollectRecordCSVSerializer.additional_group_fields.copy()
    additional_group_fields.append("data__fishbelt_transect__label")
    header_map = CollectRecordCSVSerializer.header_map.copy()
    header_map.update(
        {
            "Transect length surveyed *": "data__fishbelt_transect__len_surveyed",
            "Transect number *": "data__fishbelt_transect__number",
            "Transect label": "data__fishbelt_transect__label",
            "Width *": "data__fishbelt_transect__width",
            "Fish size bin *": "data__fishbelt_transect__size_bin",
            "Reef Slope": "data__fishbelt_transect__reef_slope",
            "Fish name *": "data__obs_belt_fishes__fish_attribute",
            "Size *": "data__obs_belt_fishes__size",
            "Count *": "data__obs_belt_fishes__count",
        }
    )

    data__fishbelt_transect__len_surveyed = serializers.IntegerField(min_value=0)
    data__fishbelt_transect__number = serializers.IntegerField(min_value=0)
    data__fishbelt_transect__label = serializers.CharField(
        allow_blank=True, required=False
    )
    data__fishbelt_transect__reef_slope = LazyChoiceField(
        choices=reef_slopes_choices, required=False, allow_null=True, allow_blank=True
    )
    data__fishbelt_transect__width = LazyChoiceField(
        choices=belt_transect_widths_choices
    )
    data__fishbelt_transect__size_bin = LazyChoiceField(choices=fish_size_bins_choices)
    data__obs_belt_fishes__fish_attribute = LazyChoiceField(
        choices=fish_attributes_choices
    )
    data__obs_belt_fishes__size = serializers.DecimalField(
        max_digits=5, decimal_places=1
    )
    data__obs_belt_fishes__count = serializers.IntegerField(min_value=0)

    def validate(self, data):
        data = super().validate(data)
        return data
