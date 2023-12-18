from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from ..fields import LazyChoiceField, NullCoercedTimeField, PositiveIntegerField
from ..models import BLEACHINGQC_PROTOCOL
from .choices import (
    benthic_attributes_choices,
    current_choices,
    growth_form_choices,
    relative_depth_choices,
    tide_choices,
    visibility_choices,
)
from .serializers import CollectRecordCSVListSerializer, CollectRecordCSVSerializer

__all__ = ["BleachingCSVSerializer"]


class BleachingCSVListSerializer(CollectRecordCSVListSerializer):
    def group_records(self, records):
        grouped_records = super().group_records(records)
        # Ensure a continuous sequence of quadrat numbers
        for rec in grouped_records:
            for n, obs in enumerate(rec["data"].get("obs_quadrat_benthic_percent")):
                obs["quadrat_number"] = n + 1
        return grouped_records


class BleachingCSVSerializer(CollectRecordCSVSerializer):
    protocol = BLEACHINGQC_PROTOCOL
    sample_unit = "quadrat_collection"
    observations_fields = [
        "data__obs_colonies_bleached",
        "data__obs_quadrat_benthic_percent",
    ]
    ordering_field = "data__obs_quadrat_benthic_percent__quadrat_number"
    additional_group_fields = CollectRecordCSVSerializer.additional_group_fields.copy()
    additional_group_fields.append("data__quadrat_collection__label")
    composite_fields = {"data__sample_event__sample_date": ["year", "month", "day"]}

    obs_colonies_bleached_fields = (
        "data__obs_colonies_bleached__attribute",
        "data__obs_colonies_bleached__growth_form",
        "data__obs_colonies_bleached__count_normal",
        "data__obs_colonies_bleached__count_pale",
        "data__obs_colonies_bleached__count_20",
        "data__obs_colonies_bleached__count_50",
        "data__obs_colonies_bleached__count_80",
        "data__obs_colonies_bleached__count_100",
        "data__obs_colonies_bleached__count_dead",
    )

    obs_quadrat_benthic_percent_fields = (
        "data__obs_quadrat_benthic_percent__quadrat_number",
        "data__obs_quadrat_benthic_percent__percent_hard",
        "data__obs_quadrat_benthic_percent__percent_soft",
        "data__obs_quadrat_benthic_percent__percent_algae",
    )

    class Meta:
        list_serializer_class = BleachingCSVListSerializer

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
    data__quadrat_collection__sample_time = NullCoercedTimeField(
        required=False,
        allow_null=True,
        label="Sample time",
        help_text="24-hour time when sample unit began (e.g. 13:15)",
    )
    data__quadrat_collection__depth = serializers.DecimalField(
        max_digits=3,
        decimal_places=1,
        label="Depth",
        help_text="Depth of sample unit, in meters (e.g. 3)",
    )
    data__quadrat_collection__label = serializers.CharField(
        allow_blank=True,
        required=False,
        default="",
        label="Label",
        help_text="Arbitrary text to distinguish sample units that are distinct but should be combined analytically (i.e. all other properties are identical). For example: 'little fish'. Rarely used.",
    )
    data__quadrat_collection__quadrat_size = serializers.DecimalField(
        max_digits=4,
        decimal_places=2,
        label="Quadrat size",
        help_text="Quadrat size used, in square meters (e.g. 1).",
    )
    data__quadrat_collection__visibility = LazyChoiceField(
        choices=visibility_choices,
        required=False,
        allow_null=True,
        allow_blank=True,
        label="Visibility",
        help_text="The horizontal distance at which an object underwater can still be identified. See relevant tab on ingestion template for choices.",
    )
    data__quadrat_collection__current = LazyChoiceField(
        choices=current_choices,
        required=False,
        allow_null=True,
        allow_blank=True,
        label="Current",
        help_text="The current/water speed during the survey. See relevant tab on ingestion template for choices.",
    )
    data__quadrat_collection__relative_depth = LazyChoiceField(
        choices=relative_depth_choices,
        required=False,
        allow_null=True,
        allow_blank=True,
        label="Relative depth",
        help_text="Depth category to distinguish surveys in the same site but at different depths. See relevant tab on ingestion template for choices.",
    )
    data__quadrat_collection__tide = LazyChoiceField(
        choices=tide_choices,
        required=False,
        allow_null=True,
        allow_blank=True,
        label="Tide",
        help_text="The tide characteristics of the survey. Falling tide is when the sea surface height is decreasing after the High tide due to the outgoing tide (ebb current); High tide occurs when the sea surface height is at the highest; Low tide occurs when the sea surface height is at the lowest; Rising tide is when the sea surface height increases after the Low tide due to the incoming tide along the coast (flood current); and Slack water is the weakest current between the flood and ebb currents. See relevant tab on ingestion template for choices.",
    )
    data__quadrat_collection__notes = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
        label="Sample unit notes",
        help_text="Notes recorded by observer for quadrat collection",
    )
    data__observers = serializers.ListField(
        child=serializers.CharField(),
        allow_empty=False,
        label="Observer emails",
        help_text="Comma-separated list of emails of sample unit observers (e.g. 'me@example.com,you@example.com').",
    )
    data__obs_colonies_bleached__attribute = LazyChoiceField(
        choices=benthic_attributes_choices,
        required=False,
        allow_null=True,
        allow_blank=True,
        label="Benthic attribute",
        help_text="Benthic attribute observed. See relevant tab on ingestion template for choices.",
    )
    data__obs_colonies_bleached__growth_form = LazyChoiceField(
        choices=growth_form_choices,
        required=False,
        allow_null=True,
        allow_blank=True,
        label="Growth form",
        help_text="Growth form of the observed benthic attribute (if applicable). See relevant tab on ingestion template for choices.",
    )
    data__obs_colonies_bleached__count_normal = PositiveIntegerField(
        required=False,
        allow_null=True,
        label="Number of colonies normal",
        help_text="Number of normal colonies, as integer (3).",
    )
    data__obs_colonies_bleached__count_pale = PositiveIntegerField(
        required=False,
        allow_null=True,
        label="Number of colonies pale",
        help_text="Number of pale colonies, as integer (3).",
    )
    data__obs_colonies_bleached__count_20 = PositiveIntegerField(
        required=False,
        allow_null=True,
        label="Number of colonies bleached 0-20% bleached",
        help_text="Number of 0-20% bleached colonies, as integer (3).",
    )
    data__obs_colonies_bleached__count_50 = PositiveIntegerField(
        required=False,
        allow_null=True,
        label="Number of colonies bleached 20-50% bleached",
        help_text="Number of 20-50% bleached colonies, as integer (3).",
    )
    data__obs_colonies_bleached__count_80 = PositiveIntegerField(
        required=False,
        allow_null=True,
        label="Number of colonies bleached 50-80% bleached",
        help_text="Number of 50-80% bleached colonies, as integer (3).",
    )
    data__obs_colonies_bleached__count_100 = PositiveIntegerField(
        required=False,
        allow_null=True,
        label="Number of colonies bleached 80-100% bleached",
        help_text="Number of 80-100% bleached colonies, as integer (3).",
    )
    data__obs_colonies_bleached__count_dead = PositiveIntegerField(
        required=False,
        allow_null=True,
        label="Number of colonies recently dead",
        help_text="Number of recently dead colonies, as integer (3).",
    )
    data__obs_quadrat_benthic_percent__quadrat_number = PositiveIntegerField(
        required=False,
        allow_null=True,
        label="Quadrat number",
        help_text="Number of quadrat in sample unit collection, as integer (e.g. 1).",
    )
    data__obs_quadrat_benthic_percent__percent_hard = serializers.DecimalField(
        default=None,
        required=False,
        max_digits=5,
        decimal_places=2,
        allow_null=True,
        label="Hard coral % cover",
        help_text="Hard coral cover as decimal percentage of quadrat total area (e.g. 33.3).",
    )
    data__obs_quadrat_benthic_percent__percent_soft = serializers.DecimalField(
        default=None,
        required=False,
        max_digits=5,
        decimal_places=2,
        allow_null=True,
        label="Soft coral % cover",
        help_text="Soft coral cover as decimal percentage of quadrat total area (e.g. 33.3).",
    )
    data__obs_quadrat_benthic_percent__percent_algae = serializers.DecimalField(
        default=None,
        required=False,
        max_digits=5,
        decimal_places=2,
        allow_null=True,
        label="Macroalgae % cover",
        help_text="Macroalgae cover as decimal percentage of quadrat total area (e.g. 33.3).",
    )

    def skip_field(self, data, field):
        empty_fields = []
        if (data.get("data__obs_colonies_bleached__attribute") or "").strip() == "":
            empty_fields = "obs_colonies_bleached_fields"
        elif (data.get("data__obs_quadrat_benthic_percent__quadrat_number") or "").strip() == "":
            empty_fields = "obs_quadrat_benthic_percent_fields"

        return field in getattr(self, empty_fields)

    def _get_original_benthic_attribute_value(self, data):
        if hasattr(self, "_attribute_col_name") is False:
            _reverse_header_map = {v: k for k, v in self.header_map.items()}
            self._attribute_col_name = _reverse_header_map.get(
                "data__obs_colonies_bleached__attribute"
            )

        _row_number = self._row_index.get(str(data["id"]))
        orig_row = self.original_data[_row_number - 2]
        return orig_row.get(self._attribute_col_name)

    def validate(self, data):
        data = super().validate(data)
        attribute_value = data.get("data__obs_colonies_bleached__attribute")
        quadrat_number = data.get("data__obs_quadrat_benthic_percent__quadrat_number")

        if not attribute_value and not quadrat_number:
            benthic_attr_name = self._get_original_benthic_attribute_value(data)
            if benthic_attr_name is not None:
                raise ValidationError(
                    f"'{benthic_attr_name}' benthic attribute has no match in MERMAID."
                )

            raise ValidationError(
                "One of 'Colonies Bleached' or 'Percent Cover' columns are required."
            )

        if data.get("data__obs_colonies_bleached__attribute") and data.get(
            "data__obs_quadrat_benthic_percent__quadrat_number"
        ):
            raise ValidationError(
                "Only one of 'Colonies Bleached' or 'Percent Cover' columns can be defined."
            )

        return data
