from django.utils.translation import gettext_lazy as _
from rest_framework import fields, serializers
from rest_framework.exceptions import ValidationError

from ..fields import LazyChoiceField
from ..models import BLEACHINGQC_PROTOCOL, BenthicAttribute, GrowthForm
from .choices import (
    build_choices,
    current_choices,
    relative_depth_choices,
    tide_choices,
    visibility_choices,
)
from .serializers import CollectRecordCSVSerializer

__all__ = ["BleachingCSVSerializer"]


class PositiveIntegerField(fields.Field):
    default_error_messages = {
        "min_value": _("Ensure this value is greater than or equal to 0.")
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.allow_null = True
        self.required = False
        self.allow_blank = True

    def to_internal_value(self, value):
        try:
            val = int(value)
        except (TypeError, ValueError):
            val = 0

        if val < 0:
            self.fail("min_value")

        return val

    def to_representation(self, value):
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0


def growth_form_choices():
    return build_choices(GrowthForm.objects.choices(order_by="name"))


def benthic_attributes_choices():
    return [
        (str(c.id), str(c.name))
        for c in BenthicAttribute.objects.all().order_by("name")
    ]


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
    header_map = CollectRecordCSVSerializer.header_map.copy()

    header_map.update(
        {
            "Sample time": "data__quadrat_collection__sample_time",
            "Depth *": "data__quadrat_collection__depth",
            "Visibility": "data__quadrat_collection__visibility",
            "Current": "data__quadrat_collection__current",
            "Relative depth": "data__quadrat_collection__relative_depth",
            "Tide": "data__quadrat_collection__tide",

            "Quadrat size *": "data__quadrat_collection__quadrat_size",
            "Label": "data__quadrat_collection__label",
            "Benthic attribute": "data__obs_colonies_bleached__attribute",
            "Growth form": "data__obs_colonies_bleached__growth_form",
            "Number of colonies normal": "data__obs_colonies_bleached__count_normal",
            "Number of colonies pale": "data__obs_colonies_bleached__count_pale",
            "Number of colonies bleached 0-20% bleached": "data__obs_colonies_bleached__count_20",
            "Number of colonies bleached 20-50% bleached": "data__obs_colonies_bleached__count_50",
            "Number of colonies bleached 50-80% bleached": "data__obs_colonies_bleached__count_80",
            "Number of colonies bleached 80-100% bleached": "data__obs_colonies_bleached__count_100",
            "Number of colonies recently dead": "data__obs_colonies_bleached__count_dead",
            "Quadrat number": "data__obs_quadrat_benthic_percent__quadrat_number",
            "Hard coral % cover": "data__obs_quadrat_benthic_percent__percent_hard",
            "Soft coral % cover": "data__obs_quadrat_benthic_percent__percent_soft",
            "Macroalgae coral % cover": "data__obs_quadrat_benthic_percent__percent_algae",
        }
    )

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

    data__quadrat_collection__sample_time = serializers.TimeField(default="00:00:00")
    data__quadrat_collection__depth = serializers.DecimalField(max_digits=3, decimal_places=1)

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
    data__obs_quadrat_benthic_percent__percent_hard = PositiveIntegerField()
    data__obs_quadrat_benthic_percent__percent_soft = PositiveIntegerField()
    data__obs_quadrat_benthic_percent__percent_algae = PositiveIntegerField()

    def skip_field(self, data, field):
        empty_fields = []
        if (data.get("data__obs_colonies_bleached__attribute") or "").strip() == "":
            empty_fields = "obs_colonies_bleached_fields"
        elif (
            data.get("data__obs_quadrat_benthic_percent__quadrat_number") or ""
        ).strip() == "":
            empty_fields = "obs_quadrat_benthic_percent_fields"

        return field in getattr(self, empty_fields)

    def validate(self, data):
        data = super().validate(data)
        if not data.get("data__obs_colonies_bleached__attribute") and not data.get(
            "data__obs_quadrat_benthic_percent__quadrat_number"
        ):
            raise ValidationError(
                "One of obs_colonies_bleached or obs_quadrat_benthic_percent is required."
            )

        if data.get("data__obs_colonies_bleached__attribute") and data.get(
            "data__obs_quadrat_benthic_percent__quadrat_number"
        ):
            raise ValidationError(
                "Only one of obs_colonies_bleached or obs_quadrat_benthic_percent should be defined."
            )

        return data

    def get_sample_event_time(self, row):
        return row.get("data__quadrat_collection__sample_time") or "00:00:00"
