from rest_framework import serializers

from ..fields import LazyChoiceField, NullCoercedTimeField, PositiveIntegerField
from ..models import BENTHICPQT_PROTOCOL
from .choices import (
    benthic_attributes_choices,
    current_choices,
    growth_form_choices,
    reef_slopes_choices,
    relative_depth_choices,
    tide_choices,
    visibility_choices,
)
from .serializers import CollectRecordCSVSerializer

__all__ = ["BenthicPhotoQTCSVSerializer"]


class BenthicPhotoQTCSVSerializer(CollectRecordCSVSerializer):
    protocol = BENTHICPQT_PROTOCOL
    sample_unit = "quadrat_transect"
    observations_fields = ["data__obs_benthic_photo_quadrats"]
    ordering_field = "data__obs_benthic_photo_quadrats__quadrat_number"
    additional_group_fields = CollectRecordCSVSerializer.additional_group_fields.copy()
    additional_group_fields.append("data__quadrat_transect__label")
    composite_fields = {"data__sample_event__sample_date": ["year", "month", "day"]}

    data__sample_event__site = serializers.CharField(label="Site", help_text="")
    data__sample_event__management = serializers.CharField(
        label="Management", help_text=""
    )
    data__sample_event__sample_date = serializers.DateField(
        label="Sample date: Year,Sample date: Month,Sample date: Day", help_text=""
    )
    data__quadrat_transect__sample_time = NullCoercedTimeField(
        required=False, allow_null=True, label="Sample time", help_text=""
    )
    data__quadrat_transect__depth = serializers.DecimalField(
        max_digits=3, decimal_places=1, label="Depth", help_text=""
    )
    data__quadrat_transect__number = serializers.IntegerField(
        min_value=0, label="Transect number", help_text=""
    )
    data__quadrat_transect__label = serializers.CharField(
        allow_blank=True,
        required=False,
        default="",
        label="Transect label",
        help_text="",
    )
    data__quadrat_transect__len_surveyed = serializers.DecimalField(
        max_digits=4, decimal_places=1, label="Transect length surveyed", help_text=""
    )
    data__quadrat_transect__num_quadrats = PositiveIntegerField(
        label="Number of quadrats", help_text=""
    )
    data__quadrat_transect__quadrat_size = serializers.DecimalField(
        max_digits=4, decimal_places=2, label="Quadrat size", help_text=""
    )
    data__quadrat_transect__quadrat_number_start = PositiveIntegerField(
        default=1, label="First quadrat number", help_text=""
    )
    data__quadrat_transect__num_points_per_quadrat = PositiveIntegerField(
        label="Number of points per quadrat", help_text=""
    )
    data__quadrat_transect__reef_slope = LazyChoiceField(
        choices=reef_slopes_choices,
        required=False,
        allow_null=True,
        allow_blank=True,
        label="Reef slope",
        help_text="",
    )
    data__quadrat_transect__visibility = LazyChoiceField(
        choices=visibility_choices,
        required=False,
        allow_null=True,
        allow_blank=True,
        label="Visibility",
        help_text="",
    )
    data__quadrat_transect__current = LazyChoiceField(
        choices=current_choices,
        required=False,
        allow_null=True,
        allow_blank=True,
        label="Current",
        help_text="",
    )
    data__quadrat_transect__relative_depth = LazyChoiceField(
        choices=relative_depth_choices,
        required=False,
        allow_null=True,
        allow_blank=True,
        label="Relative depth",
        help_text="",
    )
    data__quadrat_transect__tide = LazyChoiceField(
        choices=tide_choices,
        required=False,
        allow_null=True,
        allow_blank=True,
        label="Tide",
        help_text="",
    )
    data__quadrat_transect__notes = serializers.CharField(
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
    data__obs_benthic_photo_quadrats__quadrat_number = PositiveIntegerField(
        label="Quadrat", help_text=""
    )
    data__obs_benthic_photo_quadrats__attribute = LazyChoiceField(
        choices=benthic_attributes_choices, label="Benthic attribute", help_text=""
    )
    data__obs_benthic_photo_quadrats__growth_form = LazyChoiceField(
        choices=growth_form_choices,
        required=False,
        allow_null=True,
        allow_blank=True,
        label="Growth form",
        help_text="",
    )
    data__obs_benthic_photo_quadrats__num_points = PositiveIntegerField(
        label="Number of points", help_text=""
    )

    def validate(self, data):
        data = super().validate(data)
        return data
