from rest_framework import serializers

from ..fields import LazyChoiceField, NullCoercedTimeField
from ..models import FISHBELT_PROTOCOL
from .choices import (
    belt_transect_widths_choices,
    current_choices,
    fish_attributes_choices,
    fish_size_bins_choices,
    reef_slopes_choices,
    relative_depth_choices,
    tide_choices,
    visibility_choices,
)
from .serializers import CollectRecordCSVSerializer

__all__ = ["FishBeltCSVSerializer"]


class FishBeltCSVSerializer(CollectRecordCSVSerializer):
    protocol = FISHBELT_PROTOCOL
    sample_unit = "fishbelt_transect"
    observations_fields = ["data__obs_belt_fishes"]
    additional_group_fields = CollectRecordCSVSerializer.additional_group_fields.copy()
    additional_group_fields.append("data__fishbelt_transect__label")
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
        help_text="Date data was collected: four-digit year (e.g. 2023), two-digit month(e.g. 02), two-digit day (e.g. 28)",
    )
    data__fishbelt_transect__sample_time = NullCoercedTimeField(
        required=False,
        allow_null=True,
        label="Sample time",
        help_text="24-hour time when sample unit began (e.g. 13:15)",
    )
    data__fishbelt_transect__depth = serializers.DecimalField(
        max_digits=3,
        decimal_places=1,
        label="Depth",
        help_text="Depth of sample unit, in meters (e.g. 3)",
    )
    data__fishbelt_transect__number = serializers.IntegerField(
        min_value=0,
        label="Transect number",
        help_text="Sample unit number, as integer (e.g. 1)",
    )
    data__fishbelt_transect__label = serializers.CharField(
        allow_blank=True,
        required=False,
        default="",
        label="Transect label",
        help_text="Arbitrary text to distinguish sample units that are distinct but should be combined analytically (i.e. all other properties are identical). For example: 'little fish'. Rarely used.",
    )
    data__fishbelt_transect__len_surveyed = serializers.DecimalField(
        max_digits=4,
        decimal_places=1,
        label="Transect length surveyed",
        help_text="Length of transect for a sample unit, in meters. May include decimal (e.g. 50.0).",
    )
    data__fishbelt_transect__width = LazyChoiceField(
        choices=belt_transect_widths_choices,
        label="Width",
        help_text="Width of fish belt transect, in meters. See relevant tab on ingestion template for choices.",
    )
    data__fishbelt_transect__size_bin = LazyChoiceField(
        choices=fish_size_bins_choices,
        label="Fish size bin",
        help_text="Name of bin scheme used to estimate fish size for the transect. See relevant tab on ingestion template for choices. Choose 1 cm if the fish size recorded does not use bins.",
    )
    data__fishbelt_transect__reef_slope = LazyChoiceField(
        choices=reef_slopes_choices,
        required=False,
        allow_null=True,
        allow_blank=True,
        label="Reef slope",
        help_text="An indication of coral reef profile of the survey location. Flat is a shallow area that is nearly horizontal; Slope is a submerged sloping lower fore reef area that opens up into the open ocean (between 0 and 45 degrees angle); Wall is any seaward-facing fore reef feature with a near vertical slope (> 45 degrees angle); Crest is the breaking point between the reef flat and reef front. See relevant tab on ingestion template for choices.",
    )
    data__fishbelt_transect__visibility = LazyChoiceField(
        choices=visibility_choices,
        required=False,
        allow_null=True,
        allow_blank=True,
        label="Visibility",
        help_text="The horizontal distance at which an object underwater can still be identified. See relevant tab on ingestion template for choices.",
    )
    data__fishbelt_transect__current = LazyChoiceField(
        choices=current_choices,
        required=False,
        allow_null=True,
        allow_blank=True,
        label="Current",
        help_text="The current/water speed during the survey. See relevant tab on ingestion template for choices.",
    )
    data__fishbelt_transect__relative_depth = LazyChoiceField(
        choices=relative_depth_choices,
        required=False,
        allow_null=True,
        allow_blank=True,
        label="Relative depth",
        help_text="Depth category to distinguish surveys in the same site but at different depths. See relevant tab on ingestion template for choices.",
    )
    data__fishbelt_transect__tide = LazyChoiceField(
        choices=tide_choices,
        required=False,
        allow_null=True,
        allow_blank=True,
        label="Tide",
        help_text="The tide characteristics of the survey. Falling tide is when the sea surface height is decreasing after the High tide due to the outgoing tide (ebb current); High tide occurs when the sea surface height is at the highest; Low tide occurs when the sea surface height is at the lowest; Rising tide is when the sea surface height increases after the Low tide due to the incoming tide along the coast (flood current); and Slack water is the weakest current between the flood and ebb currents. See relevant tab on ingestion template for choices.",
    )
    data__fishbelt_transect__notes = serializers.CharField(
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
    data__obs_belt_fishes__fish_attribute = LazyChoiceField(
        choices=fish_attributes_choices,
        label="Fish name",
        help_text="Name of the fish species, genus, or family observed. See relevant tab on ingestion template for choices.",
    )
    data__obs_belt_fishes__size = serializers.DecimalField(
        max_digits=5,
        decimal_places=1,
        label="Size",
        help_text="Size of fish observed, in cm (e.g. 4.5 or 5-10).",
    )
    data__obs_belt_fishes__count = serializers.IntegerField(
        min_value=0,
        label="Count",
        help_text="Number of fish observed, with the same name and size, as integer (e.g. 7).",
    )

    def validate(self, data):
        data = super().validate(data)
        return data
