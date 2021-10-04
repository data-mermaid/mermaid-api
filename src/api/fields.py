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

    def to_internal_value(self, data):
        # Adding a cache to the choices that are
        # used during serialization. Will see a performance gain
        # if a field has a large number of choices but only uses
        # a small number of them when deserializing records.

        if data == "" and self.allow_blank:
            return ""

        try:
            str_data = str(data)
            val = None
            if str_data not in self._cached_choices:
                val = self.choice_strings_to_values[str_data]
                if val is not None:
                    self._cached_choices[str_data] = val
            else:
                val = self._cached_choices[str_data]
            return val
        except KeyError:
            self.fail("invalid_choice", input=data)

    choices = property(_get_choices, _set_choices)
