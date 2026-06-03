from rest_framework import serializers

from ..fields import LazyChoiceField, NullCoercedTimeField
from ..models import MACROINVERTEBRATE_PROTOCOL
from .choices import (
    current_choices,
    invert_attributes_choices,
    invert_belt_transect_widths_choices,
    invert_size_bins_choices,
    reef_slopes_choices,
    relative_depth_choices,
    tide_choices,
    visibility_choices,
)
from .serializers import CollectRecordCSVSerializer

__all__ = ["MacroInvertebrateCSVSerializer"]


class MacroInvertebrateCSVSerializer(CollectRecordCSVSerializer):
    protocol = MACROINVERTEBRATE_PROTOCOL
    sample_unit = "beltinvert_transect"
    observations_fields = ["data__obs_belt_inverts"]
    additional_group_fields = CollectRecordCSVSerializer.additional_group_fields.copy()
    additional_group_fields.append("data__beltinvert_transect__label")
    composite_fields = {"data__sample_event__sample_date": ["year", "month", "day"]}

    data__sample_event__site = serializers.CharField(
        label="Site",
        help_text="A unique name of a site where data was collected. Every site must be defined before ingestion and set up in the project in the web app.",
    )
    data__sample_event__management = serializers.CharField(
        label="Management",
        help_text="Name of management regime in effect for the site where data was collected on the date of collection. Must be defined before ingestion and set up in the project in the web app.",
    )
    data__sample_event__sample_date = serializers.DateField(
        label="Sample date: Year,Sample date: Month,Sample date: Day",
        help_text="Date data was collected: four-digit year (e.g. 2023), two-digit month (e.g. 02), two-digit day (e.g. 28)",
    )
    data__beltinvert_transect__sample_time = NullCoercedTimeField(
        required=False,
        allow_null=True,
        label="Sample time",
        help_text="24-hour time when sample unit began (e.g. 13:15)",
    )
    data__beltinvert_transect__depth = serializers.DecimalField(
        max_digits=3,
        decimal_places=1,
        label="Depth",
        help_text="Depth of sample unit, in meters (e.g. 3)",
    )
    data__beltinvert_transect__number = serializers.IntegerField(
        min_value=0,
        label="Transect number",
        help_text="Sample unit number, as integer (e.g. 1)",
    )
    data__beltinvert_transect__label = serializers.CharField(
        allow_blank=True,
        required=False,
        default="",
        label="Transect label",
        help_text="Arbitrary text to distinguish sample units that are distinct but should be combined analytically.",
    )
    data__beltinvert_transect__len_surveyed = serializers.DecimalField(
        max_digits=4,
        decimal_places=1,
        label="Transect length surveyed",
        help_text="Length of transect for a sample unit, in meters (e.g. 50.0).",
    )
    data__beltinvert_transect__width = LazyChoiceField(
        choices=invert_belt_transect_widths_choices,
        label="Width",
        help_text="Width of macroinvertebrate belt transect, in meters. See relevant tab on ingestion template for choices.",
    )
    data__beltinvert_transect__size_bin = LazyChoiceField(
        choices=invert_size_bins_choices,
        required=False,
        allow_null=True,
        allow_blank=True,
        label="Size bin",
        help_text="Size bin scheme used for the transect. See relevant tab on ingestion template for choices.",
    )
    data__beltinvert_transect__reef_slope = LazyChoiceField(
        choices=reef_slopes_choices,
        required=False,
        allow_null=True,
        allow_blank=True,
        label="Reef slope",
        help_text="Reef slope profile of the survey location. See relevant tab on ingestion template for choices.",
    )
    data__beltinvert_transect__visibility = LazyChoiceField(
        choices=visibility_choices,
        required=False,
        allow_null=True,
        allow_blank=True,
        label="Visibility",
        help_text="Horizontal distance at which an object can be identified underwater. See relevant tab for choices.",
    )
    data__beltinvert_transect__current = LazyChoiceField(
        choices=current_choices,
        required=False,
        allow_null=True,
        allow_blank=True,
        label="Current",
        help_text="Current/water speed during the survey. See relevant tab on ingestion template for choices.",
    )
    data__beltinvert_transect__relative_depth = LazyChoiceField(
        choices=relative_depth_choices,
        required=False,
        allow_null=True,
        allow_blank=True,
        label="Relative depth",
        help_text="Depth category to distinguish surveys at the same site but at different depths. See relevant tab for choices.",
    )
    data__beltinvert_transect__tide = LazyChoiceField(
        choices=tide_choices,
        required=False,
        allow_null=True,
        allow_blank=True,
        label="Tide",
        help_text="Tide characteristics during the survey. See relevant tab on ingestion template for choices.",
    )
    data__beltinvert_transect__notes = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
        label="Sample unit notes",
        help_text="Notes recorded by observer for transect",
    )
    data__observers = serializers.ListField(
        child=serializers.CharField(),
        allow_empty=False,
        label="Observer emails",
        help_text="Comma-separated list of emails of sample unit observers (e.g. 'me@example.com,you@example.com').",
    )
    data__obs_belt_inverts__invert_attribute = LazyChoiceField(
        choices=invert_attributes_choices,
        label="Invert name",
        help_text="Name of the macroinvertebrate species, genus, family, order, class, or group of interest observed. See relevant tab on ingestion template for choices.",
    )
    data__obs_belt_inverts__count = serializers.IntegerField(
        min_value=1,
        label="Count",
        help_text="Number of individuals observed, as integer (e.g. 3).",
    )
    data__obs_belt_inverts__size = serializers.DecimalField(
        max_digits=5,
        decimal_places=1,
        required=False,
        allow_null=True,
        label="Size",
        help_text="Size of individual observed, in cm (e.g. 4.5).",
    )
    data__obs_belt_inverts__include = serializers.BooleanField(
        required=False,
        default=True,
        label="Include",
        help_text="Whether to include this observation in aggregations (True/False). Defaults to True.",
    )
    data__obs_belt_inverts__notes = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
        label="Observation notes",
        help_text="Notes for this observation",
    )
