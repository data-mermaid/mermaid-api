from rest_framework import fields
from rest_framework import serializers


class LazyChoiceField(serializers.ChoiceField):
    _grouped_choices = None

    @property
    def grouped_choices(self):
        if self._grouped_choices is None:
            self._grouped_choices = fields.to_choices_dict(self._choices())
        return self._grouped_choices

    @property
    def choice_strings_to_values(self):
        return {str(key): key for key in self.choices}

    def _get_choices(self):
        return fields.flatten_choices_dict(self.grouped_choices)

    def _set_choices(self, choices):
        self._choices = choices

    choices = property(_get_choices, _set_choices)
