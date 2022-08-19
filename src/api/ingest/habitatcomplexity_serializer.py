from rest_framework import serializers

from ..fields import LazyChoiceField
from ..models import HABITATCOMPLEXITY_PROTOCOL, HabitatComplexityScore, ReefSlope
from .choices import (
    build_choices,
    current_choices,
    relative_depth_choices,
    tide_choices,
    visibility_choices,
)
from .serializers import CollectRecordCSVSerializer

__all__ = ["HabitatComplexityCSVSerializer"]


def score_choices():
    return build_choices(
        HabitatComplexityScore.objects.choices(order_by="name"), val_key="val"
    )


def reef_slopes_choices():
    return build_choices(ReefSlope.objects.choices(order_by="name"))


class HabitatComplexityCSVSerializer(CollectRecordCSVSerializer):
    protocol = HABITATCOMPLEXITY_PROTOCOL
    sample_unit = "benthic_transect"
    observations_fields = ["data__obs_habitat_complexities"]
    ordering_field = "data__obs_habitat_complexities__interval"
    additional_group_fields = CollectRecordCSVSerializer.additional_group_fields.copy()
    additional_group_fields.append("data__benthic_transect__label")
    header_map = {
        "Site *": "data__sample_event__site",
        "Management *": "data__sample_event__management",
        "Sample date: Year *": "data__sample_event__sample_date__year",
        "Sample date: Month *": "data__sample_event__sample_date__month",
        "Sample date: Day *": "data__sample_event__sample_date__day",
        "Sample time": "data__benthic_transect__sample_time",
        "Depth *": "data__benthic_transect__depth",
        "Transect length surveyed *": "data__benthic_transect__len_surveyed",
        "Interval size *": "data__interval_size",
        "Transect number *": "data__benthic_transect__number",
        "Transect label": "data__benthic_transect__label",
        "Reef slope": "data__benthic_transect__reef_slope",
        "Visibility": "data__benthic_transect__visibility",
        "Current": "data__benthic_transect__current",
        "Relative depth": "data__benthic_transect__relative_depth",
        "Tide": "data__benthic_transect__tide",
        "Sample unit notes": "data__benthic_transect__notes",
        "Observer emails *": "data__observers",
        "Observation interval *": "data__obs_habitat_complexities__interval",
        "Habitat complexity score *": "data__obs_habitat_complexities__score",
    }

    data__benthic_transect__sample_time = serializers.TimeField(
        required=False, allow_null=True
    )
    data__benthic_transect__depth = serializers.DecimalField(
        max_digits=3, decimal_places=1
    )
    data__benthic_transect__visibility = LazyChoiceField(
        choices=visibility_choices, required=False, allow_null=True, allow_blank=True
    )
    data__benthic_transect__current = LazyChoiceField(
        choices=current_choices, required=False, allow_null=True, allow_blank=True
    )
    data__benthic_transect__relative_depth = LazyChoiceField(
        choices=relative_depth_choices,
        required=False,
        allow_null=True,
        allow_blank=True,
    )
    data__benthic_transect__tide = LazyChoiceField(
        choices=tide_choices, required=False, allow_null=True, allow_blank=True
    )
    data__interval_size = serializers.DecimalField(max_digits=4, decimal_places=2)
    data__benthic_transect__len_surveyed = serializers.IntegerField(min_value=0)
    data__benthic_transect__number = serializers.IntegerField(min_value=0)
    data__benthic_transect__label = serializers.CharField(
        allow_blank=True, required=False, default=""
    )
    data__benthic_transect__reef_slope = LazyChoiceField(
        choices=reef_slopes_choices, required=False, allow_null=True, allow_blank=True
    )
    data__benthic_transect__notes = serializers.CharField(
        required=False, allow_blank=True, default=""
    )
    data__obs_habitat_complexities__interval = serializers.DecimalField(
        max_digits=7, decimal_places=2
    )
    data__obs_habitat_complexities__score = LazyChoiceField(choices=score_choices)

    def get_sample_event_time(self, row):
        return row.get("data__benthic_transect__sample_time")

    def clean(self, data):
        data = super().clean(data)
        interval_start = data.get("data__interval_start")
        if interval_start is None or interval_start.strip() == "":
            data["data__interval_start"] = data.get("data__interval_size")
        return data

    def validate(self, data):
        data = super().validate(data)
        return data
