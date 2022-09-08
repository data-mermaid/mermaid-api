from rest_framework import serializers

from ..fields import LazyChoiceField
from ..models import HABITATCOMPLEXITY_PROTOCOL
from .choices import (
    current_choices,
    reef_slopes_choices,
    relative_depth_choices,
    score_choices,
    tide_choices,
    visibility_choices,
)
from .serializers import CollectRecordCSVSerializer

__all__ = ["HabitatComplexityCSVSerializer"]


class HabitatComplexityCSVSerializer(CollectRecordCSVSerializer):
    protocol = HABITATCOMPLEXITY_PROTOCOL
    sample_unit = "benthic_transect"
    observations_fields = ["data__obs_habitat_complexities"]
    ordering_field = "data__obs_habitat_complexities__interval"
    additional_group_fields = CollectRecordCSVSerializer.additional_group_fields.copy()
    additional_group_fields.append("data__benthic_transect__label")
    composite_fields = {"data__sample_event__sample_date": ["year", "month", "day"]}

    data__sample_event__site = serializers.CharField(label="Site", help_text="")
    data__sample_event__management = serializers.CharField(
        label="Management", help_text=""
    )
    data__sample_event__sample_date = serializers.DateField(
        label="Sample date: Year,Sample date: Month,Sample date: Day", help_text=""
    )
    data__benthic_transect__sample_time = serializers.TimeField(
        required=False, allow_null=True, label="Sample time", help_text=""
    )
    data__benthic_transect__depth = serializers.DecimalField(
        max_digits=3, decimal_places=1, label="Depth", help_text=""
    )
    data__benthic_transect__number = serializers.IntegerField(
        min_value=0, label="Transect number", help_text=""
    )
    data__benthic_transect__label = serializers.CharField(
        allow_blank=True,
        required=False,
        default="",
        label="Transect label",
        help_text="",
    )
    data__benthic_transect__len_surveyed = serializers.DecimalField(
        max_digits=4, decimal_places=1, label="Transect length surveyed", help_text=""
    )
    data__interval_size = serializers.DecimalField(
        max_digits=4, decimal_places=2, label="Interval size", help_text=""
    )
    data__benthic_transect__reef_slope = LazyChoiceField(
        choices=reef_slopes_choices,
        required=False,
        allow_null=True,
        allow_blank=True,
        label="Reef slope",
        help_text="",
    )
    data__benthic_transect__visibility = LazyChoiceField(
        choices=visibility_choices,
        required=False,
        allow_null=True,
        allow_blank=True,
        label="Visibility",
        help_text="",
    )
    data__benthic_transect__current = LazyChoiceField(
        choices=current_choices,
        required=False,
        allow_null=True,
        allow_blank=True,
        label="Current",
        help_text="",
    )
    data__benthic_transect__relative_depth = LazyChoiceField(
        choices=relative_depth_choices,
        required=False,
        allow_null=True,
        allow_blank=True,
        label="Relative depth",
        help_text="",
    )
    data__benthic_transect__tide = LazyChoiceField(
        choices=tide_choices,
        required=False,
        allow_null=True,
        allow_blank=True,
        label="Tide",
        help_text="",
    )
    data__benthic_transect__notes = serializers.CharField(
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
    data__obs_habitat_complexities__interval = serializers.DecimalField(
        max_digits=7, decimal_places=2, label="Observation interval", help_text=""
    )
    data__obs_habitat_complexities__score = LazyChoiceField(
        choices=score_choices, label="Habitat complexity score", help_text=""
    )

    def clean(self, data):
        data = super().clean(data)
        interval_start = data.get("data__interval_start")
        if interval_start is None or interval_start.strip() == "":
            data["data__interval_start"] = data.get("data__interval_size")
        return data

    def validate(self, data):
        data = super().validate(data)
        return data
