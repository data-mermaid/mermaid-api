from rest_framework import serializers

from ..fields import LazyChoiceField
from ..models import FISHBELT_PROTOCOL, BeltTransectWidth, FishSizeBin, ReefSlope
from ..models.view_models import FishAttributeView
from .choices import (
    build_choices,
    current_choices,
    relative_depth_choices,
    tide_choices,
    visibility_choices,
)
from .serializers import CollectRecordCSVSerializer

__all__ = ["FishBeltCSVSerializer"]


def reef_slopes_choices():
    return build_choices(ReefSlope.objects.choices(order_by="name"))


def belt_transect_widths_choices():
    return build_choices(BeltTransectWidth.objects.choices(order_by="name"), "name")


def fish_size_bins_choices():
    return build_choices(FishSizeBin.objects.choices(order_by="val"), "val")


def fish_attributes_choices():
    return [
        (str(c.id), str(c.name))
        for c in FishAttributeView.objects.all().order_by("name")
    ]


class FishBeltCSVSerializer(CollectRecordCSVSerializer):
    protocol = FISHBELT_PROTOCOL
    sample_unit = "fishbelt_transect"
    observations_fields = ["data__obs_belt_fishes"]
    additional_group_fields = CollectRecordCSVSerializer.additional_group_fields.copy()
    additional_group_fields.append("data__fishbelt_transect__label")
    header_map = {  # order preserved
        "data__sample_event__site": {"label": "Site *", "description": ""},
        "data__sample_event__management": {"label": "Management *", "description": ""},
        "data__sample_event__sample_date__year": {"label": "Sample date: Year *", "description": ""},
        "data__sample_event__sample_date__month": {"label": "Sample date: Month *", "description": ""},
        "data__sample_event__sample_date__day": {"label": "Sample date: Day *", "description": ""},
        "data__fishbelt_transect__sample_time": {"label": "Sample time", "description": ""},
        "data__fishbelt_transect__depth": {"label": "Depth *", "description": ""},
        "data__fishbelt_transect__number": {"label": "Transect number *", "description": ""},
        "data__fishbelt_transect__label": {"label": "Transect label", "description": ""},
        "data__fishbelt_transect__len_surveyed": {"label": "Transect length surveyed *", "description": ""},
        "data__fishbelt_transect__width": {"label": "Width *", "description": ""},
        "data__fishbelt_transect__size_bin": {"label": "Fish size bin *", "description": ""},
        "data__fishbelt_transect__reef_slope": {"label": "Reef slope", "description": ""},
        "data__fishbelt_transect__visibility": {"label": "Visibility", "description": ""},
        "data__fishbelt_transect__current": {"label": "Current", "description": ""},
        "data__fishbelt_transect__relative_depth": {"label": "Relative depth", "description": ""},
        "data__fishbelt_transect__tide": {"label": "Tide", "description": ""},
        "data__fishbelt_transect__notes": {"label": "Sample unit notes", "description": ""},
        "data__observers": {"label": "Observer emails *", "description": ""},
        "data__obs_belt_fishes__fish_attribute": {"label": "Fish name *", "description": ""},
        "data__obs_belt_fishes__size": {"label": "Size *", "description": ""},
        "data__obs_belt_fishes__count": {"label": "Count *", "description": ""},
    }

    data__fishbelt_transect__sample_time = serializers.TimeField(
        required=False, allow_null=True
    )
    data__fishbelt_transect__depth = serializers.DecimalField(
        max_digits=3, decimal_places=1
    )
    data__fishbelt_transect__visibility = LazyChoiceField(
        choices=visibility_choices, required=False, allow_null=True, allow_blank=True
    )
    data__fishbelt_transect__current = LazyChoiceField(
        choices=current_choices, required=False, allow_null=True, allow_blank=True
    )
    data__fishbelt_transect__relative_depth = LazyChoiceField(
        choices=relative_depth_choices,
        required=False,
        allow_null=True,
        allow_blank=True,
    )
    data__fishbelt_transect__tide = LazyChoiceField(
        choices=tide_choices, required=False, allow_null=True, allow_blank=True
    )
    data__fishbelt_transect__len_surveyed = serializers.DecimalField(
        max_digits=4, decimal_places=1
    )
    data__fishbelt_transect__number = serializers.IntegerField(min_value=0)
    data__fishbelt_transect__label = serializers.CharField(
        allow_blank=True, required=False, default=""
    )
    data__fishbelt_transect__reef_slope = LazyChoiceField(
        choices=reef_slopes_choices, required=False, allow_null=True, allow_blank=True
    )
    data__fishbelt_transect__notes = serializers.CharField(
        required=False, allow_blank=True, default=""
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

    def get_sample_event_time(self, row):
        return row.get("data__fishbelt_transect__sample_time")
