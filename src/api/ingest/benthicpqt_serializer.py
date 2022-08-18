from rest_framework import serializers

from ..fields import LazyChoiceField, PositiveIntegerField
from ..models import BENTHICPQT_PROTOCOL, BenthicAttribute, GrowthForm, ReefSlope
from .choices import (
    build_choices,
    current_choices,
    relative_depth_choices,
    tide_choices,
    visibility_choices,
)
from .serializers import CollectRecordCSVSerializer

__all__ = ["BenthicPhotoQTCSVSerializer"]


def growth_form_choices():
    return build_choices(GrowthForm.objects.choices(order_by="name"))


def reef_slopes_choices():
    return build_choices(ReefSlope.objects.choices(order_by="name"))


def benthic_attributes_choices():
    return [
        (str(c.id), str(c.name))
        for c in BenthicAttribute.objects.all().order_by("name")
    ]


class BenthicPhotoQTCSVSerializer(CollectRecordCSVSerializer):
    protocol = BENTHICPQT_PROTOCOL
    sample_unit = "quadrat_transect"
    observations_fields = ["data__obs_benthic_photo_quadrats"]
    ordering_field = "data__obs_benthic_photo_quadrats__quadrat_number"
    additional_group_fields = CollectRecordCSVSerializer.additional_group_fields.copy()
    additional_group_fields.append("data__quadrat_transect__label")
    header_map = {
        "Site *": "data__sample_event__site",
        "Management *": "data__sample_event__management",
        "Sample date: Year *": "data__sample_event__sample_date__year",
        "Sample date: Month *": "data__sample_event__sample_date__month",
        "Sample date: Day *": "data__sample_event__sample_date__day",
        "Sample time": "data__quadrat_transect__sample_time",
        "Depth *": "data__quadrat_transect__depth",
        "Transect length surveyed *": "data__quadrat_transect__len_surveyed",
        "Number of quadrats *": "data__quadrat_transect__num_quadrats",
        "Quadrat size *": "data__quadrat_transect__quadrat_size",
        "Number of points per quadrat *": "data__quadrat_transect__num_points_per_quadrat",
        "Transect number *": "data__quadrat_transect__number",
        "Transect label": "data__quadrat_transect__label",
        "Reef slope": "data__quadrat_transect__reef_slope",
        "Visibility": "data__quadrat_transect__visibility",
        "Current": "data__quadrat_transect__current",
        "Relative depth": "data__quadrat_transect__relative_depth",
        "Tide": "data__quadrat_transect__tide",
        "Sample unit notes": "data__quadrat_transect__notes",
        "Observer emails *": "data__observers",
        "Quadrat *": "data__obs_benthic_photo_quadrats__quadrat_number",
        "Benthic attribute *": "data__obs_benthic_photo_quadrats__attribute",
        "Growth form": "data__obs_benthic_photo_quadrats__growth_form",
        "Number of points *": "data__obs_benthic_photo_quadrats__num_points",
    }

    data__quadrat_transect__sample_time = serializers.TimeField(
        required=False, allow_null=True
    )
    data__quadrat_transect__depth = serializers.DecimalField(
        max_digits=3, decimal_places=1
    )
    data__quadrat_transect__visibility = LazyChoiceField(
        choices=visibility_choices, required=False, allow_null=True, allow_blank=True
    )
    data__quadrat_transect__current = LazyChoiceField(
        choices=current_choices, required=False, allow_null=True, allow_blank=True
    )
    data__quadrat_transect__relative_depth = LazyChoiceField(
        choices=relative_depth_choices,
        required=False,
        allow_null=True,
        allow_blank=True,
    )
    data__quadrat_transect__tide = LazyChoiceField(
        choices=tide_choices, required=False, allow_null=True, allow_blank=True
    )
    data__quadrat_transect__quadrat_size = serializers.DecimalField(
        max_digits=4, decimal_places=2
    )
    data__quadrat_transect__len_surveyed = serializers.DecimalField(
        max_digits=4, decimal_places=1
    )
    data__quadrat_transect__number = serializers.IntegerField(min_value=0)
    data__quadrat_transect__label = serializers.CharField(
        allow_blank=True, required=False, default=""
    )
    data__quadrat_transect__reef_slope = LazyChoiceField(
        choices=reef_slopes_choices, required=False, allow_null=True, allow_blank=True
    )
    data__quadrat_transect__notes = serializers.CharField(
        required=False, allow_blank=True, default=""
    )
    data__quadrat_transect__num_quadrats = PositiveIntegerField()
    data__quadrat_transect__num_points_per_quadrat = PositiveIntegerField()
    data__obs_benthic_photo_quadrats__attribute = LazyChoiceField(
        choices=benthic_attributes_choices
    )
    data__obs_benthic_photo_quadrats__growth_form = LazyChoiceField(
        choices=growth_form_choices, required=False, allow_null=True, allow_blank=True
    )
    data__obs_benthic_photo_quadrats__quadrat_number = PositiveIntegerField()
    data__obs_benthic_photo_quadrats__num_points = PositiveIntegerField()

    def get_sample_event_time(self, row):
        return row.get("data__quadrat_transect__sample_time")

    def validate(self, data):
        data = super().validate(data)
        return data
