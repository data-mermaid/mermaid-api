from rest_framework import serializers

from ..models import FishAttributeView
from ..resources.choices import ChoiceViewSet
from .serializers import CollectRecordCSVSerializer, build_choices


class FishBeltCSVSerializer(CollectRecordCSVSerializer):
    protocol = "fishbelt"
    observations_field = "data__obs_belt_fishes"
    header_map = CollectRecordCSVSerializer.header_map
    header_map.update(
        {
            "Transect length surveyed *": "data__fishbelt_transect__len_surveyed",
            "Transect number *": "data__fishbelt_transect__number",
            "Transect label": "data__fishbelt_transect__label",
            "Width *": "data__fishbelt_transect__width",
            "Fish size bin *": "data__fishbelt_transect__size_bin",
            "Reef Slope": "data__fishbelt_transect__reef_slope",
            "Fish name *": "data__obs_belt_fishes__fish_attribute",
            "Size *": "data__obs_belt_fishes__size",
            "Count *": "data__obs_belt_fishes__count",
        }
    )

    _choices = ChoiceViewSet().get_choices()
    reef_slopes_choices = [
        (str(c["id"]), c["val"]) for c in _choices["reefslopes"]["data"]
    ]

    belt_transect_widths_choices = [
        (str(c["id"]), str(c["val"])) for c in _choices["belttransectwidths"]["data"]
    ]

    fish_size_bins_choices = [
        (str(c["id"]), str(c["val"])) for c in _choices["fishsizebins"]["data"]
    ]

    fish_attributes_choices = [
        (str(ba.id), ba.name) for ba in FishAttributeView.objects.all().order_by("name")
    ]

    data__fishbelt_transect__len_surveyed = serializers.IntegerField(min_value=0)
    data__fishbelt_transect__number = serializers.IntegerField(min_value=0)
    data__fishbelt_transect__label = serializers.CharField(
        allow_blank=True, required=False
    )
    data__fishbelt_transect__reef_slope = serializers.ChoiceField(
        choices=reef_slopes_choices, required=False, allow_null=True, allow_blank=True
    )
    data__fishbelt_transect__width = serializers.ChoiceField(
        choices=belt_transect_widths_choices
    )
    data__fishbelt_transect__size_bin = serializers.ChoiceField(
        choices=fish_size_bins_choices
    )
    data__obs_belt_fishes__fish_attribute = serializers.ChoiceField(
        choices=fish_attributes_choices
    )
    data__obs_belt_fishes__size = serializers.DecimalField(
        max_digits=5, decimal_places=1
    )
    data__obs_belt_fishes__count = serializers.IntegerField(min_value=0)

    def validate(self, data):
        data = super().validate(data)
        return data
