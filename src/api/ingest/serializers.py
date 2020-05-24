import uuid
from collections import OrderedDict
from collections.abc import Mapping, Sequence
from operator import itemgetter

from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.fields import empty
from rest_framework.serializers import ListSerializer, Serializer

from api.decorators import timeit
from .. import utils
from ..fields import LazyChoiceField
from ..models import CollectRecord, Current, RelativeDepth, Tide, Visibility

__all__ = [
    "CollectRecordCSVListSerializer",
    "CollectRecordCSVSerializer",
    "build_choices",
]


def build_choices(choices, val_key="name"):
    return [(str(c["id"]), str(c[val_key])) for c in choices]


def visibility_choices():
    return build_choices(Visibility.objects.choices(order_by="val"))


def current_choices():
    return build_choices(Current.objects.choices(order_by="name"))


def relative_depth_choices():
    return build_choices(RelativeDepth.objects.choices(order_by="name"))


def tide_choices():
    return build_choices(Tide.objects.choices(order_by="name"))


class CollectRecordCSVListSerializer(ListSerializer):
    obs_field_identifier = "data__obs_"

    # Track original record order
    _row_index = None

    def split_list_fields(self, field_name, data, choices=None):
        val = data.get(field_name, empty)
        if val == empty:
            return

        if choices:
            data[field_name] = [choices.get(s.strip().lower()) for s in val.split(",")]
        else:
            data[field_name] = [s.strip() for s in val.split(",")]

    def map_column_names(self, row):
        header_map = self.child.header_map
        return {
            (header_map[k.strip()] if k.strip() in header_map else k): v
            for k, v in row.items()
        }

    def assign_choices(self, row, choices_sets):
        for name, field in self.child.fields.items():
            val = field.get_value(row)
            choices = choices_sets.get(name)
            if choices is None:
                continue
            try:
                val = self._lower(val)
                row[name] = choices.get(val)
            except (ValueError, TypeError):
                row[name] = None

    def get_sample_event_date(self, row):
        missing_fields = []
        if "data__sample_event__sample_date__year" not in row:
            missing_fields.append("data__sample_event__sample_date__year")
        if "data__sample_event__sample_date__month" not in row:
            missing_fields.append("data__sample_event__sample_date__month")
        if "data__sample_event__sample_date__day" not in row:
            missing_fields.append("data__sample_event__sample_date__day")

        if missing_fields:
            field_map = self.child.reverse_kv_lookup(self.child.header_map)
            _field_names = [field_map.get(mf) for mf in missing_fields]
            raise ValueError("{} missing".format(", ".join(_field_names)))

        return "{}-{}-{}".format(
            row["data__sample_event__sample_date__year"],
            row["data__sample_event__sample_date__month"],
            row["data__sample_event__sample_date__day"],
        )

    def get_sample_event_time(self, row):
        return row.get("data__sample_event__sample_time") or "00:00:00"

    def remove_extra_data(self, row):
        field_names = set(self.child.fields.keys())
        row_keys = set(row.keys())
        diff_keys = row_keys.difference(field_names)

        for name in diff_keys:
            del row[name]

    def _lower(self, val):
        if isinstance(val, str):
            return val.lower()
        return val

    def _get_reverse_choices(self, field):
        return dict((self._lower(v), k) for k, v in field.choices.items())

    def get_choices_sets(self):
        choices = dict()
        for name, field in self.child.fields.items():
            if hasattr(field, "choices"):
                choices[name] = self._get_reverse_choices(field)
            elif (
                hasattr(self.child, "project_choices")
                and name in self.child.project_choices
            ):
                choices[name] = self.child.project_choices[name]

        return choices

    def sort_records(self, data):
        if (
            hasattr(self.child, "ordering_field") is False
            or self.child.ordering_field is None
        ):
            return data

        return sorted(data, key=lambda item: item.get(self.child.ordering_field))

    def format_data(self, data):
        assert (
            hasattr(self.child, "protocol") and self.child.protocol is not None
        ), "protocol is required serializer property"

        assert (
            hasattr(self.child, "header_map") is True
            or self.child.header_map is not None
        ), "header_map is a required serializer property"

        assert (
            hasattr(self.child, "error_row_offset") is True
            or isinstance(self.child.error_row_offset, int) is False
        ), "error_row_offset is must be an int"

        if hasattr(self.child, "error_row_offset"):
            error_row_offset = self.child.error_row_offset
        else:
            error_row_offset = 1

        fmt_rows = []
        choices_sets = self.get_choices_sets()
        protocol = self.child.protocol
        self._row_index = dict()
        for n, row in enumerate(data):
            fmt_row = self.map_column_names(row)
            pk = str(uuid.uuid4())
            self._row_index[pk] = n + 1 + error_row_offset
            fmt_row["id"] = pk
            fmt_row["stage"] = CollectRecord.SAVED_STAGE
            fmt_row["data__sample_event__sample_date"] = self.get_sample_event_date(
                fmt_row
            )
            fmt_row["data__sample_event__sample_time"] = self.get_sample_event_time(
                fmt_row
            )
            fmt_row["data__protocol"] = protocol

            self.remove_extra_data(fmt_row)
            self.assign_choices(fmt_row, choices_sets)
            self.split_list_fields("data__observers", fmt_row)

            fmt_rows.append(fmt_row)

        self._formatted_records = fmt_rows
        return fmt_rows

    def validate(self, data):
        # Validate common Transect level fields
        return data

    def run_validation(self, data=empty):
        return super().run_validation(data=self.format_data(data))

    @classmethod
    def create_key(cls, record, keys, delimiter="__"):
        hash = []
        for k in sorted(keys):
            v = utils.get_value(record, k, delimiter=delimiter)
            if isinstance(v, list):
                if isinstance(v[0], dict):
                    dictkeys = [cls.create_key(skey, skey.keys()) for skey in v]
                    v = ",".join(sorted(dictkeys))
                else:
                    v = ",".join([str(s) for s in sorted(v)])
            elif isinstance(v, dict):
                v = ",".join([str(v[i]) for i in sorted(v)])
            else:
                v = str(v)
            hash.append(v)
        return "::".join(hash)

    def get_group_by_fields(self):
        group_fields = []
        for name, field in self.child.get_fields().items():
            if (
                field.required is True
                and name.startswith(self.obs_field_identifier) is False
                and name.lower() not in self.child.excluded_group_fields
            ):
                group_fields.append(name)
        if self.child.additional_group_fields:
            group_fields.extend(self.child.additional_group_fields)
        return group_fields

    def group_records(self, records):
        group_fields = self.get_group_by_fields()
        groups = OrderedDict()
        for record in records:
            key = self.create_key(record, group_fields)
            obs_list = [
                utils.get_value(record, obs_field)
                for obs_field in self.child.observations_fields
            ]

            if key not in groups:
                for obs_field, obs in zip(self.child.observations_fields, obs_list):
                    if obs is None:
                        utils.set_value(record, obs_field, value=[])
                        continue
                    utils.set_value(record, obs_field, value=[obs])
                groups[key] = record
            else:
                for obs_field, obs in zip(self.child.observations_fields, obs_list):
                    if obs is None:
                        continue
                    utils.get_value(groups[key], obs_field).append(obs)

        return self.sort_records(groups.values())

    def create(self, validated_data):
        records = super().create(validated_data)
        output = self.group_records(records)

        objs = [
            CollectRecord(
                id=rec["id"],
                stage=rec["stage"],
                project_id=rec["project"],
                profile_id=rec["profile"],
                data=rec["data"],
            )
            for rec in output
        ]
        return CollectRecord.objects.bulk_create(objs)

    @property
    def formatted_errors(self):
        errors = self.errors
        format_error = self.child.format_error

        fmt_errors = []
        for error, rec in zip(errors, self._formatted_records):
            if bool(error) is True:
                fmt_error = format_error(error)
                fmt_error["$row_number"] = self._row_index[rec["id"]]
                fmt_errors.append(fmt_error)

        return sorted(fmt_errors, key=itemgetter("$row_number"))


class CollectRecordCSVSerializer(Serializer):
    protocol = None
    observations_fields = None
    error_row_offset = 1
    header_map = {
        "Site *": "data__sample_event__site",
        "Management *": "data__sample_event__management",
        "Sample date: Year *": "data__sample_event__sample_date__year",
        "Sample date: Month *": "data__sample_event__sample_date__month",
        "Sample date: Day *": "data__sample_event__sample_date__day",
        "Sample time": "data__sample_event__sample_time",
        "Depth *": "data__sample_event__depth",
        "Interval size": "data__interval_size",
        "Visibility": "data__sample_event__visibility",
        "Current": "data__sample_event__current",
        "Relative depth": "data__sample_event__relative_depth",
        "Tide": "data__sample_event__tide",
        "Notes": "data__sample_event__notes",
        "Observer emails *": "data__observers",
    }

    # By Default:
    # - required fields are used
    # - "id" is excluded
    # - "observations_fields" fields are ignored
    additional_group_fields = []
    excluded_group_fields = ["id"]

    _reverse_choices = {}

    # PROJECT RELATED CHOICES
    project_choices = {
        "data__sample_event__site": None,
        "data__sample_event__management": None,
    }

    # FIELDS
    id = serializers.UUIDField(format="hex_verbose")
    stage = serializers.IntegerField()
    project = serializers.UUIDField(format="hex_verbose")
    profile = serializers.UUIDField(format="hex_verbose")
    data__protocol = serializers.CharField(required=True, allow_blank=False)

    data__sample_event__site = serializers.CharField()
    data__sample_event__management = serializers.CharField()
    data__sample_event__sample_date = serializers.DateField()
    data__sample_event__sample_time = serializers.TimeField(default="00:00:00")
    data__sample_event__depth = serializers.DecimalField(max_digits=3, decimal_places=1)

    data__sample_event__visibility = LazyChoiceField(
        choices=visibility_choices, required=False, allow_null=True, allow_blank=True
    )
    data__sample_event__current = LazyChoiceField(
        choices=current_choices, required=False, allow_null=True, allow_blank=True
    )
    data__sample_event__relative_depth = LazyChoiceField(
        choices=relative_depth_choices,
        required=False,
        allow_null=True,
        allow_blank=True,
    )
    data__sample_event__tide = LazyChoiceField(
        choices=tide_choices, required=False, allow_null=True, allow_blank=True
    )
    data__sample_event__notes = serializers.CharField(required=False, allow_blank=True)

    data__observers = serializers.ListField(
        child=serializers.CharField(), allow_empty=False
    )

    class Meta:
        list_serializer_class = CollectRecordCSVListSerializer

    def __init__(self, data=None, instance=None, project_choices=None, **kwargs):
        if instance is not None:
            raise NotImplementedError("instance argument not implemented")
        if isinstance(data, Mapping):
            self.original_data = data.copy()
        elif isinstance(data, Sequence) and isinstance(data, str) is False:
            self.original_data = [d for d in data]
        else:
            self.original_data = None

        if project_choices:
            self.project_choices = project_choices

        super().__init__(instance=None, data=data, **kwargs)

    @classmethod
    def many_init(cls, *args, **kwargs):
        if "data" in kwargs and isinstance(kwargs["data"], (dict, OrderedDict)):
            kwargs["data"] = [kwargs["data"]]
        return super(CollectRecordCSVSerializer, cls).many_init(*args, **kwargs)

    def get_initial(self):
        if not isinstance(self._original_data, Mapping):
            return OrderedDict()

        return OrderedDict(
            [
                (field_name, field.get_value(self._original_data))
                for field_name, field in self.fields.items()
                if (field.get_value(self._original_data) == empty)
                and not field.read_only
            ]
        )

    def clean(self, data):
        return data

    def run_validation(self, data=empty):
        if data is not empty:
            data = self.clean(data)
        return super().run_validation(data)

    def validate_data__observers(self, val):
        project_profiles = self.project_choices.get("project_profiles")
        val = val or []
        for email in val:
            if email.lower() not in project_profiles:
                raise ValidationError("{} doesn't exist".format(email))
        return val

    def validate(self, data):
        # Validate common Transect level fields
        return super().validate(data)

    def create_path(self, field_path, node, val):
        path = field_path.pop(0)
        if path not in node:
            if len(field_path) >= 1:
                node[path] = dict()
                self.create_path(field_path, node[path], val)
            else:
                node[path] = val
        else:
            if len(field_path) >= 1:

                self.create_path(field_path, node[path], val)
            else:
                node[path] = val
        return node

    def create(self, validated_data):
        output = validated_data.copy()
        for name, field in self.fields.items():
            if self.skip_field(output, name) is True:
                continue
            field_path = field.field_name.split("__")
            val = validated_data.get(name)
            output = self.create_path(field_path, output, val)

        # Need to serialize observers after validation to avoid
        # unique id errors
        project_profiles = self.project_choices.get("project_profiles")
        ob_emails = output["data"]["observers"]
        output["data"]["observers"] = [
            project_profiles[ob_email.lower()]
            for ob_email in ob_emails
            if ob_email.lower() in project_profiles
        ]

        return output

    def reverse_kv_lookup(self, lookup):
        return dict(zip(lookup.values(), lookup.keys()))

    def format_error(self, record_errors):
        fmt_errs = dict()
        field_map = self.reverse_kv_lookup(self.header_map)
        for k, v in record_errors.items():
            display = field_map.get(k) or k
            fmt_errs[display] = {"description": v}
        return fmt_errs

    @property
    def formatted_errors(self):
        errors = self.errors
        return self.format_error(errors)

    def skip_field(self, data, field):
        return False
