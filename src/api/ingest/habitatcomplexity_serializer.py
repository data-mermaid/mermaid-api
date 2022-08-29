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
        "data__sample_event__site": {"label": "Site *", "description": ""},
        "data__sample_event__management": {"label": "Management *", "description": ""},
        "data__sample_event__sample_date__year": {"label": "Sample date: Year *", "description": ""},
        "data__sample_event__sample_date__month": {"label": "Sample date: Month *", "description": ""},
        "data__sample_event__sample_date__day": {"label": "Sample date: Day *", "description": ""},
        "data__benthic_transect__sample_time": {"label": "Sample time", "description": ""},
        "data__benthic_transect__depth": {"label": "Depth *", "description": ""},
        "data__benthic_transect__len_surveyed": {"label": "Transect length surveyed *", "description": ""},
        "data__interval_size": {"label": "Interval size *", "description": ""},
        "data__benthic_transect__number": {"label": "Transect number *", "description": ""},
        "data__benthic_transect__label": {"label": "Transect label", "description": ""},
        "data__benthic_transect__reef_slope": {"label": "Reef slope", "description": ""},
        "data__benthic_transect__visibility": {"label": "Visibility", "description": ""},
        "data__benthic_transect__current": {"label": "Current", "description": ""},
        "data__benthic_transect__relative_depth": {"label": "Relative depth", "description": ""},
        "data__benthic_transect__tide": {"label": "Tide", "description": ""},
        "data__benthic_transect__notes": {"label": "Sample unit notes", "description": ""},
        "data__observers": {"label": "Observer emails *", "description": ""},
        "data__obs_habitat_complexities__interval": {"label": "Observation interval *", "description": ""},
        "data__obs_habitat_complexities__score": {"label": "Habitat complexity score *", "description": ""},
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
