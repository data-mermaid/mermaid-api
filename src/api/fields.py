from django.utils.translation import gettext_lazy as _
from rest_framework import fields, serializers


class LazyChoiceField(serializers.ChoiceField):
    _grouped_choices = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._flattened_choices = None
        self._cached_choices = {}

    @property
    def grouped_choices(self):
        if self._grouped_choices is None:
            self._grouped_choices = fields.to_choices_dict(self._choices())
        return self._grouped_choices

    @property
    def choice_strings_to_values(self):
        return {str(key): key for key in self.choices}

    def _get_choices(self):
        if self._flattened_choices is None:
            self._flattened_choices = fields.flatten_choices_dict(self.grouped_choices)
        return self._flattened_choices

    def _set_choices(self, choices):
        self._choices = choices
        self._flattened_choices = None
        self._cached_choices = {}

    def _check_nulls(self, value):
        if (
            (value is not None and value != "")
            or (value == "" and self.allow_blank)
            or (value is None and self.allow_null)
        ):
            return

        self.fail("null", input=value)

    def to_internal_value(self, value):
        # Adding a cache to the choices that are
        # used during serialization. Will see a performance gain
        # if a field has a large number of choices but only uses
        # a small number of them when deserializing records.

        self._check_nulls(value)
        if value is None or value == "":
            return None

        try:
            str_data = str(value)
            val = None
            if str_data not in self._cached_choices:
                val = self.choice_strings_to_values[str_data]
                if val is not None:
                    self._cached_choices[str_data] = val
            else:
                val = self._cached_choices[str_data]
            return val
        except KeyError:
            self.fail("invalid_choice", input=value)

    choices = property(_get_choices, _set_choices)


class PositiveIntegerField(fields.Field):
    default_error_messages = {"min_value": _("Ensure this value is greater than or equal to 0.")}

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.default = kwargs.get("default", 0)

    def to_internal_value(self, value):
        try:
            val = int(value)
        except (TypeError, ValueError):
            val = self.default

        if val is not None and val < 0:
            self.fail("min_value")

        return val

    def to_representation(self, value):
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0


class NullCoercedTimeField(fields.TimeField):
    def to_internal_value(self, value):
        if self.allow_null is True and isinstance(value, str) and value.strip() == "":
            return None
        return super().to_internal_value(value)
