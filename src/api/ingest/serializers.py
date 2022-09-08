import uuid
from collections import OrderedDict
from collections.abc import Mapping, Sequence
from operator import itemgetter

from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.fields import empty
from rest_framework.serializers import ListSerializer, Serializer

from .. import utils
from ..models import CollectRecord

__all__ = ["CollectRecordCSVListSerializer", "CollectRecordCSVSerializer"]


class CollectRecordCSVListSerializer(ListSerializer):
    obs_field_identifier = "data__obs_"
    _formatted_records = None
    _sample_events = dict()

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
        return {self.child.get_schemafield(k)[0]: v for k, v in row.items()}

    def assign_choices(self, row, choices_sets):
        for name, field in self.child.fields.items():
            val = field.get_value(row)
            choices = choices_sets.get(name)
            if choices is None:
                continue
            try:
                val = self._lower(val)
                choices = {label.lower(): value for label, value in choices.items()}
                row[name] = choices.get(val)
            except (ValueError, TypeError):
                row[name] = None

    def get_sample_event_date(self, row):
        if "data__sample_event__sample_date__year" not in row:
            return None
        if "data__sample_event__sample_date__month" not in row:
            return None
        if "data__sample_event__sample_date__day" not in row:
            return None

        return "{}-{}-{}".format(
            row["data__sample_event__sample_date__year"],
            row["data__sample_event__sample_date__month"],
            row["data__sample_event__sample_date__day"],
        )

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
        return dict((v, k) for k, v in field.choices.items())

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
            hasattr(self.child, "error_row_offset") is True
            or isinstance(self.child.error_row_offset, int) is False
        ), "error_row_offset is must be an int"

        if hasattr(self.child, "error_row_offset"):
            error_row_offset = self.child.error_row_offset
        else:
            error_row_offset = 1

        fmt_rows = []
        # Handle multiple-select project choices separately
        choices_sets = {
            k: v for k, v in self.get_choices_sets().items() if k != "data__observers"
        }
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
            fmt_row["data__protocol"] = protocol

            self.remove_extra_data(fmt_row)
            self.assign_choices(fmt_row, choices_sets)
            self.split_list_fields("data__observers", fmt_row)

            fmt_rows.append(fmt_row)

        self._formatted_records = fmt_rows
        self.child._row_index = self._row_index
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
        records = self.sort_records(records)
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

        return groups.values()

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
        self._formatted_records = self._formatted_records or []
        for error, rec in zip(errors, self._formatted_records):
            if bool(error) is True:
                fmt_error = format_error(error)
                fmt_error["$row_number"] = self._row_index[rec["id"]]
                fmt_errors.append(fmt_error)

        return sorted(fmt_errors, key=itemgetter("$row_number"))


class CollectRecordCSVSerializer(Serializer):
    protocol = None
    sample_unit = None
    observations_fields = None
    error_row_offset = 1

    # By Default:
    # - required fields are used
    # - "id" is excluded
    # - "observations_fields" fields are ignored
    additional_group_fields = []
    excluded_group_fields = ["id"]

    # Inheritors can declare 'composite' fields, which map from the actual field name
    # to a list of suffixes corresponding in the same order to comma-separated labels
    # stored in the field's `label` field. Example:
    #     composite_fields = {"data__sample_event__sample_date": ["year", "month", "day"]}
    composite_fields = []

    # PROJECT RELATED CHOICES
    project_choices = {
        "data__sample_event__site": None,
        "data__sample_event__management": None,
        "data__observers": None,
    }

    # Fields common to all ingestion serializers, excluded from schema definition.
    # All fields declared in inheritors will be used for schema generation and validation;
    # the order of those field declarations is preserved in csv headers and json schema lists.
    id = serializers.UUIDField(format="hex_verbose")
    stage = serializers.IntegerField()
    project = serializers.UUIDField(format="hex_verbose")
    profile = serializers.UUIDField(format="hex_verbose")
    data__protocol = serializers.CharField(required=True, allow_blank=False)

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
        project_profiles = self.project_choices.get("data__observers")
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
        project_profiles = self.project_choices.get("data__observers")
        ob_emails = output["data"]["observers"]
        output["data"]["observers"] = [
            project_profiles[ob_email.lower()]
            for ob_email in ob_emails
            if ob_email.lower() in project_profiles
        ]

        return output

    def get_schemafields(self):
        base_csv_serializer_fields = self.__class__.__mro__[1]().fields
        return {
            k: v for k, v in self.fields.items() if k not in base_csv_serializer_fields
        }

    def get_field_labels(self, field):
        return [
            f"{label} *" if field.required else label
            for label in field.label.split(",")
        ]

    def get_schema_labels(self):
        schema_labels = []
        for fieldname, field in self.get_schemafields().items():
            labels = self.get_field_labels(field)
            schema_labels.extend(labels)
        return schema_labels

    def get_schemafield_name(self, field, header):
        fieldname = getattr(field, "field_name", "unknown_field")
        if fieldname in self.composite_fields:
            suffix = "__"
            for n, label in enumerate(self.get_field_labels(field)):
                if label in header:
                    suffix = f"{suffix}{self.composite_fields[field.field_name][n]}"
            fieldname = f"{fieldname}{suffix}"
        return fieldname

    def get_schemafield(self, label):
        schema_fields = self.get_schemafields()
        for fieldname, field in schema_fields.items():
            if label.strip() in self.get_field_labels(field):
                fieldname = self.get_schemafield_name(field, label)
                return fieldname, field
        return label, None

    def format_error(self, record_errors):
        fmt_errs = dict()
        for k, v in record_errors.items():
            fieldname, field = self.get_schemafield(k)
            fmt_errs[fieldname] = {"description": v}
        return fmt_errs

    @property
    def formatted_errors(self):
        errors = self.errors
        return self.format_error(errors)

    def skip_field(self, data, field):
        return False
