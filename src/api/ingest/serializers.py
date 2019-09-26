# project*
# profile*
# data__protocol
# Site *,data__sample_event__site__id*
# Management *,data__sample_event__management__id*
# Sample date: Year *,data__sample_event__sample_date*
# Sample date: Month *,data__sample_event__sample_date*
# Sample date: Day *,data__sample_event__sample_date*
# Sample time,data__sample_event__sample_time*
# Depth *,data__sample_event__depth*
# Transect length surveyed*,data__benthic_transect__len_surveyed*
# Transect number*,data__benthic_transect__number*
# Transect label,data__benthic_transect__label
# Interval size*,data__interval_size*
# Visibility,data__sample_event__visibility
# Current,data__sample_event__current
# Relative depth,data__sample_event__relative_depth
# Tide,data__sample_event__tide
# Reef Slope,data__benthic_transect__reef_slope
# Notes,data__sample_event__notes
# Observer name*,data__observers__profile_name*
# Observation interval*,data__obs_benthic_pits__interval*
# Benthic attribute*,data__obs_benthic_pits__attribute*
# Growth form,data__obs_benthic_pits__growth_form*


from collections import OrderedDict
from rest_framework import serializers
from rest_framework.fields import empty
from rest_framework.serializers import Serializer
from rest_framework.exceptions import ParseError
from collections.abc import Mapping, Iterable

from ..resources.choices import ChoiceViewSet
from ..resources.observer import ObserverSerializer
from ..models import BenthicAttribute, ProjectProfile, Site, Management
from ..exceptions import check_uuid


def build_choices(key, choices):
    return [(str(c["id"]), str(c["name"])) for c in choices[key]["data"]]


# class OberverSerializer(Serializer):
# #       {
# #         "id": "1f1f5d79-41f5-451d-a46f-3586a2f9d422",
# #         "role": 90,
# #         "profile": "0e6dc8a8-ae45-4c19-813c-6d688ed6a7c3",
# #         "project": "ff68e385-266a-4a55-801b-3487f607b913",
# #         "is_admin": true,
# #         "created_by": null,
# #         "created_on": "2019-09-17T20:09:57.598338Z",
# #         "updated_by": null,
# #         "updated_on": "2019-09-17T20:09:57.598373Z",
# #         "is_collector": true,
# #         "profile_name": "Dustin Sampson"
# #       }


class CollectRecordCSVSerializer(Serializer):
    header_map = {
        "Site *": "data__sample_event__site__id",
        "Management *": "data__sample_event__management__id",
        "Sample date: Year *": "data__sample_event__sample_date__year",
        "Sample date: Month *": "data__sample_event__sample_date__month",
        "Sample date: Day *": "data__sample_event__sample_date__day",
        "Sample time": "data__sample_event__sample_time",
        "Depth *": "data__sample_event__depth",
        "Transect length surveyed": "data__benthic_transect__len_surveyed",
        "Transect number": "data__benthic_transect__number",
        "Transect label": "data__benthic_transect__label",
        "Interval size": "data__interval_size",
        "Visibility": "data__sample_event__visibility",
        "Current": "data__sample_event__current",
        "Relative depth": "data__sample_event__relative_depth",
        "Tide": "data__sample_event__tide",
        "Reef Slope": "data__benthic_transect__reef_slope",
        "Notes": "data__sample_event__notes",
        "Observer name": "data__observer__id",
        "Observation interval": "data__obs_benthic_pits__interval",
        "Benthic attribute": "data__obs_benthic_pits__attribute",
        "Growth form": "data__obs_benthic_pits__growth_form",
    }

    # CHOICES
    _choices = ChoiceViewSet().get_choices()
    visibility_choices = build_choices("visibilities", _choices)
    current_choices = build_choices("currents", _choices)
    relative_depth_choices = build_choices("relativedepths", _choices)
    tide_choices = build_choices("tides", _choices)
    reef_slopes_choices = build_choices("reefslopes", _choices)
    benthic_attributes_choices = [
        (str(ba.id), ba.name) for ba in BenthicAttribute.objects.all()
    ]
    growth_form_choices = build_choices("growthforms", _choices)

    _reverse_choices = {}

    # PROJECT RELATED CHOICES
    _cached_project_choices = {}
    _project_choices = {
        "data__observers__profile_name": None,
        "data__sample_event__site__id": None,
        "data__sample_event__management__id": None,
    }

    # FIELDS
    project = serializers.UUIDField(format="hex_verbose")
    profile = serializers.UUIDField(format="hex_verbose")

    data__sample_event__site__id = serializers.CharField()
    data__sample_event__management__id = serializers.CharField()
    data__sample_event__sample_date = serializers.DateField()
    data__sample_event__sample_time = serializers.TimeField()
    data__sample_event__depth = serializers.DecimalField(max_digits=3, decimal_places=1)

    data__sample_event__visibility = serializers.ChoiceField(
        choices=visibility_choices, required=False, allow_null=True, allow_blank=True
    )
    data__sample_event__current = serializers.ChoiceField(
        choices=current_choices, required=False, allow_null=True, allow_blank=True
    )
    data__sample_event__relative_depth = serializers.ChoiceField(
        choices=relative_depth_choices,
        required=False,
        allow_null=True,
        allow_blank=True,
    )
    data__sample_event__tide = serializers.ChoiceField(
        choices=tide_choices, required=False, allow_null=True, allow_blank=True
    )
    data__sample_event__notes = serializers.CharField(required=False, allow_blank=True)

    data__observer__id = serializers.CharField()

    def __init__(self, data=None, instance=None, **kwargs):
        if instance is not None:
            raise NotImplementedError("instance argument not implemented")

        if isinstance(data, Mapping):
            self.original_data = data.copy()
        elif isinstance(data, Iterable) and isinstance(data, str):
            self.original_data = [d for d in data]
        else:
            self.original_data = None

        super().__init__(instance=None, data=data, **kwargs)

    def get_project_choices(self, project):
        if self._project_choices.get("data__observers__profile_name") is None:
            self._project_choices["data__observers__profile_name"] = {
                pp.profile_name.lower(): str(pp.id)
                for pp in ProjectProfile.objects.filter(project_id=project)
            }

        if self._project_choices.get("data__sample_event__site__id") is None:
            self._project_choices["data__sample_event__site__id"] = {
                s.name.lower(): str(s.id)
                for s in Site.objects.filter(project_id=project)
            }

        if self._project_choices.get("data__sample_event__management__id") is None:
            self._project_choices["data__sample_event__management__id"] = {
                m.name.lower(): str(m.id)
                for m in Management.objects.filter(project_id=project)
            }
        return self._project_choices

    def map_column_names(self, data):
        if self.header_map is None:
            return data

        mapped_col_data = OrderedDict()
        for k, v in data.items():
            display_name = k.strip()
            if display_name in self.header_map:
                field_name = self.header_map[display_name]
            else:
                field_name = display_name
            mapped_col_data[field_name] = v

        return mapped_col_data

    def get_initial(self):
        if not isinstance(self._original_data, Mapping):
            return OrderedDict()

        return OrderedDict(
            [
                (field_name, field.get_value(self._original_data))
                for field_name, field in self.fields.items()
                if (field.get_value(self._original_data) is not empty)
                and not field.read_only
            ]
        )

    def lookup(self, value, choices):
        if isinstance(value, str):
            value = value.strip()
            try:
                _ = check_uuid(value)
                return value
            except ParseError:
                value = value.lower()
        return dict(choices).get(value)

    def validate(self, data):
        # Validate common Transect level fields
        return data

    def remove_extra_data(self, data):
        filtered_data = OrderedDict()
        for name, field in self.fields.items():
            if name in data:
                filtered_data[name] = data[name]
        return filtered_data

    def _get_reverse_choices(self, field):
        field_name = field.field_name
        if field_name not in self._reverse_choices:
            self._reverse_choices[field_name] = dict(
                (v.lower(), k) for k, v in field.choices.items()
            )
        return self._reverse_choices[field_name]

    def assign_choices(self, data):
        project_choices = self.get_project_choices(data["project"])
        for name, field in self.fields.items():
            val = field.get_value(data)
            choices = None
            if hasattr(field, "choices"):
                choices = self._get_reverse_choices(field)
            elif name in project_choices:
                choices = project_choices[name]

            if choices:
                try:
                    data[name] = choices.get(val.lower())
                except (ValueError, TypeError):
                    data[name] = None
        return data

    def get_sample_event_date(self, data):
        return "{}-{}-{}".format(
            data["data__sample_event__sample_date__year"],
            data["data__sample_event__sample_date__month"],
            data["data__sample_event__sample_date__day"],
        )

    def format_data(self, data):
        data = self.map_column_names(data)
        data["data__sample_event__sample_date"] = self.get_sample_event_date(data)
        filtered_data = self.remove_extra_data(data)
        filtered_data = self.assign_choices(filtered_data)
        return filtered_data

    def run_validation(self, data=empty):
        return super().run_validation(data=self.format_data(data))

    def create(self):
        return dict()
        # s.validated_data


class BenthicPITCSVSerializer(CollectRecordCSVSerializer):
    pass

