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
    composite_fields = {"data__sample_event__sample_date": ["year", "month", "day"]}

    data__sample_event__site = serializers.CharField(label="Site", help_text="")
    data__sample_event__management = serializers.CharField(
        label="Management", help_text=""
    )

    data__sample_event__sample_date = serializers.DateField(
        label="Sample date: Year,Sample date: Month,Sample date: Day", help_text=""
    )

    data__fishbelt_transect__sample_time = serializers.TimeField(
        required=False, allow_null=True, label="Sample time", help_text=""
    )
    data__fishbelt_transect__depth = serializers.DecimalField(
        max_digits=3, decimal_places=1, label="Depth", help_text=""
    )
    data__fishbelt_transect__number = serializers.IntegerField(
        min_value=0, label="Transect number", help_text=""
    )
    data__fishbelt_transect__label = serializers.CharField(
        allow_blank=True,
        required=False,
        default="",
        label="Transect label",
        help_text="",
    )
    data__fishbelt_transect__len_surveyed = serializers.DecimalField(
        max_digits=4, decimal_places=1, label="Transect length surveyed", help_text=""
    )
    data__fishbelt_transect__width = LazyChoiceField(
        choices=belt_transect_widths_choices, label="Width", help_text=""
    )
    data__fishbelt_transect__size_bin = LazyChoiceField(
        choices=fish_size_bins_choices, label="Fish size bin", help_text=""
    )
    data__fishbelt_transect__reef_slope = LazyChoiceField(
        choices=reef_slopes_choices,
        required=False,
        allow_null=True,
        allow_blank=True,
        label="Reef slope",
        help_text="",
    )
    data__fishbelt_transect__visibility = LazyChoiceField(
        choices=visibility_choices,
        required=False,
        allow_null=True,
        allow_blank=True,
        label="Visibility",
        help_text="",
    )
    data__fishbelt_transect__current = LazyChoiceField(
        choices=current_choices,
        required=False,
        allow_null=True,
        allow_blank=True,
        label="Current",
        help_text="",
    )
    data__fishbelt_transect__relative_depth = LazyChoiceField(
        choices=relative_depth_choices,
        required=False,
        allow_null=True,
        allow_blank=True,
        label="Relative depth",
        help_text="",
    )
    data__fishbelt_transect__tide = LazyChoiceField(
        choices=tide_choices,
        required=False,
        allow_null=True,
        allow_blank=True,
        label="Tide",
        help_text="",
    )
    data__fishbelt_transect__notes = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
        label="Sample unit notes",
        help_text="",
    )
    data__observers = serializers.ListField(
        child=serializers.CharField(),
        allow_empty=False,
        label="Observer emails",
        help_text="",
    )
    data__obs_belt_fishes__fish_attribute = LazyChoiceField(
        choices=fish_attributes_choices, label="Fish name", help_text=""
    )
    data__obs_belt_fishes__size = serializers.DecimalField(
        max_digits=5, decimal_places=1, label="Size", help_text=""
    )
    data__obs_belt_fishes__count = serializers.IntegerField(
        min_value=0, label="Count", help_text=""
    )

    def validate(self, data):
        data = super().validate(data)
        return data

    def get_sample_event_time(self, row):
        return row.get("data__fishbelt_transect__sample_time")
