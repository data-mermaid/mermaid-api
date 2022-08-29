from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from ..fields import LazyChoiceField, PositiveIntegerField
from ..models import BLEACHINGQC_PROTOCOL, BenthicAttribute, GrowthForm
from .choices import (
    build_choices,
    current_choices,
    relative_depth_choices,
    tide_choices,
    visibility_choices,
)
from .serializers import CollectRecordCSVListSerializer, CollectRecordCSVSerializer

__all__ = ["BleachingCSVSerializer"]


def growth_form_choices():
    return build_choices(GrowthForm.objects.choices(order_by="name"))


def benthic_attributes_choices():
    return [
        (str(c.id), str(c.name))
        for c in BenthicAttribute.objects.all().order_by("name")
    ]


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
    header_map = {
        "data__sample_event__site": {"label": "Site *", "description": ""},
        "data__sample_event__management": {"label": "Management *", "description": ""},
        "data__sample_event__sample_date__year": {"label": "Sample date: Year *", "description": ""},
        "data__sample_event__sample_date__month": {"label": "Sample date: Month *", "description": ""},
        "data__sample_event__sample_date__day": {"label": "Sample date: Day *", "description": ""},
        "data__quadrat_collection__sample_time": {"label": "Sample time", "description": ""},
        "data__quadrat_collection__depth": {"label": "Depth *", "description": ""},
        "data__quadrat_collection__quadrat_size": {"label": "Quadrat size *", "description": ""},
        "data__quadrat_collection__label": {"label": "Label", "description": ""},
        "data__quadrat_collection__visibility": {"label": "Visibility", "description": ""},
        "data__quadrat_collection__current": {"label": "Current", "description": ""},
        "data__quadrat_collection__relative_depth": {"label": "Relative depth", "description": ""},
        "data__quadrat_collection__tide": {"label": "Tide", "description": ""},
        "data__quadrat_collection__notes": {"label": "Sample unit notes", "description": ""},
        "data__observers": {"label": "Observer emails *", "description": ""},
        "data__obs_colonies_bleached__attribute": {"label": "Benthic attribute", "description": ""},
        "data__obs_colonies_bleached__growth_form": {"label": "Growth form", "description": ""},
        "data__obs_colonies_bleached__count_normal": {"label": "Number of colonies normal", "description": ""},
        "data__obs_colonies_bleached__count_pale": {"label": "Number of colonies pale", "description": ""},
        "data__obs_colonies_bleached__count_20": {"label": "Number of colonies bleached 0-20% bleached", "description": ""},
        "data__obs_colonies_bleached__count_50": {"label": "Number of colonies bleached 20-50% bleached", "description": ""},
        "data__obs_colonies_bleached__count_80": {"label": "Number of colonies bleached 50-80% bleached", "description": ""},
        "data__obs_colonies_bleached__count_100": {"label": "Number of colonies bleached 80-100% bleached", "description": ""},
        "data__obs_colonies_bleached__count_dead": {"label": "Number of colonies recently dead", "description": ""},
        "data__obs_quadrat_benthic_percent__quadrat_number": {"label": "Quadrat number", "description": ""},
        "data__obs_quadrat_benthic_percent__percent_hard": {"label": "Hard coral % cover", "description": ""},
        "data__obs_quadrat_benthic_percent__percent_soft": {"label": "Soft coral % cover", "description": ""},
        "data__obs_quadrat_benthic_percent__percent_algae": {"label": "Macroalgae % cover", "description": ""},
    }

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

    data__quadrat_collection__sample_time = serializers.TimeField(
        required=False, allow_null=True
    )
    data__quadrat_collection__depth = serializers.DecimalField(
        max_digits=3, decimal_places=1
    )
    data__quadrat_collection__visibility = LazyChoiceField(
        choices=visibility_choices, required=False, allow_null=True, allow_blank=True
    )
    data__quadrat_collection__current = LazyChoiceField(
        choices=current_choices, required=False, allow_null=True, allow_blank=True
    )
    data__quadrat_collection__relative_depth = LazyChoiceField(
        choices=relative_depth_choices,
        required=False,
        allow_null=True,
        allow_blank=True,
    )
    data__quadrat_collection__tide = LazyChoiceField(
        choices=tide_choices, required=False, allow_null=True, allow_blank=True
    )
    data__quadrat_collection__notes = serializers.CharField(
        required=False, allow_blank=True, default=""
    )
    data__quadrat_collection__quadrat_size = serializers.DecimalField(
        max_digits=4, decimal_places=2
    )
    data__quadrat_collection__label = serializers.CharField(
        allow_blank=True, required=False, default=""
    )
    data__obs_colonies_bleached__attribute = LazyChoiceField(
        choices=benthic_attributes_choices,
        required=False,
        allow_null=True,
        allow_blank=True,
    )
    data__obs_colonies_bleached__growth_form = LazyChoiceField(
        choices=growth_form_choices, required=False, allow_null=True, allow_blank=True
    )
    data__obs_colonies_bleached__count_normal = PositiveIntegerField()
    data__obs_colonies_bleached__count_pale = PositiveIntegerField()
    data__obs_colonies_bleached__count_20 = PositiveIntegerField()
    data__obs_colonies_bleached__count_50 = PositiveIntegerField()
    data__obs_colonies_bleached__count_80 = PositiveIntegerField()
    data__obs_colonies_bleached__count_100 = PositiveIntegerField()
    data__obs_colonies_bleached__count_dead = PositiveIntegerField()
    data__obs_quadrat_benthic_percent__quadrat_number = PositiveIntegerField()
    data__obs_quadrat_benthic_percent__percent_hard = serializers.DecimalField(
        default=None, required=False, max_digits=5, decimal_places=2, allow_null=True
    )
    data__obs_quadrat_benthic_percent__percent_soft = serializers.DecimalField(
        default=None, required=False, max_digits=5, decimal_places=2, allow_null=True
    )
    data__obs_quadrat_benthic_percent__percent_algae = serializers.DecimalField(
        default=None, required=False, max_digits=5, decimal_places=2, allow_null=True
    )

    def skip_field(self, data, field):
        empty_fields = []
        if (data.get("data__obs_colonies_bleached__attribute") or "").strip() == "":
            empty_fields = "obs_colonies_bleached_fields"
        elif (
            data.get("data__obs_quadrat_benthic_percent__quadrat_number") or ""
        ).strip() == "":
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

    def get_sample_event_time(self, row):
        return row.get("data__quadrat_collection__sample_time")
