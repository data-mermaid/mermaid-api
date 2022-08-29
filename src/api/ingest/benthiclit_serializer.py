from rest_framework import serializers

from ..fields import LazyChoiceField
from ..models import BENTHICLIT_PROTOCOL, BenthicAttribute, GrowthForm, ReefSlope
from .choices import (
    build_choices,
    current_choices,
    relative_depth_choices,
    tide_choices,
    visibility_choices,
)
from .serializers import CollectRecordCSVSerializer

__all__ = ["BenthicLITCSVSerializer"]


def growth_form_choices():
    return build_choices(GrowthForm.objects.choices(order_by="name"))


def reef_slopes_choices():
    return build_choices(ReefSlope.objects.choices(order_by="name"))


def benthic_attributes_choices():
    return [
        (str(c.id), str(c.name))
        for c in BenthicAttribute.objects.all().order_by("name")
    ]


class BenthicLITCSVSerializer(CollectRecordCSVSerializer):
    protocol = BENTHICLIT_PROTOCOL
    sample_unit = "benthic_transect"
    observations_fields = ["data__obs_benthic_lits"]
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
        "data__benthic_transect__number": {"label": "Transect number *", "description": ""},
        "data__benthic_transect__label": {"label": "Transect label", "description": ""},
        "data__benthic_transect__reef_slope": {"label": "Reef slope", "description": ""},
        "data__benthic_transect__visibility": {"label": "Visibility", "description": ""},
        "data__benthic_transect__current": {"label": "Current", "description": ""},
        "data__benthic_transect__relative_depth": {"label": "Relative depth", "description": ""},
        "data__benthic_transect__tide": {"label": "Tide", "description": ""},
        "data__benthic_transect__notes": {"label": "Sample unit notes", "description": ""},
        "data__observers": {"label": "Observer emails *", "description": ""},
        "data__obs_benthic_lits__attribute": {"label": "Benthic attribute *", "description": ""},
        "data__obs_benthic_lits__growth_form": {"label": "Growth form", "description": ""},
        "data__obs_benthic_lits__length": {"label": "Observation length *", "description": ""},
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
    data__obs_benthic_lits__attribute = LazyChoiceField(
        choices=benthic_attributes_choices
    )
    data__obs_benthic_lits__growth_form = LazyChoiceField(
        choices=growth_form_choices, required=False, allow_null=True, allow_blank=True
    )
    data__obs_benthic_lits__length = serializers.IntegerField()

    def get_sample_event_time(self, row):
        return row.get("data__benthic_transect__sample_time")

    def validate(self, data):
        data = super().validate(data)
        return data
