import re
from collections import OrderedDict

from ..utils import is_match


class ReportSerializer(object):
    fields = None
    non_field_columns = None
    include_additional_fields = False
    show_display_fields = False

    def __init__(
        self,
        queryset=None,
        ignore_select_related=False,
        include_additional_fields=False,
        show_display_fields=False,
    ):
        self.queryset = queryset
        self.ignore_select_related = ignore_select_related
        self.include_additional_fields = include_additional_fields
        self.show_display_fields = show_display_fields
        self.cache = {}

    def get_fields(self):
        if self.fields is None:
            raise ValueError("fields not defined")

        fields = list(self.fields)
        if self.include_additional_fields is True:
            fields += getattr(self, "additional_fields", [])

        if hasattr(self, "excluded_fields"):
            patterns = [re.compile(c) for c in self.excluded_fields]
            return [c for c in fields if is_match(c.display, patterns) is False]

        return fields

    def _get_column_paths(self):
        return [f.column_path for f in self.get_fields() if hasattr(f, "column_path")]

    def _get_prepared_queryset(self, qs):
        if self.ignore_select_related is False:
            qs = qs.select_related()

        column_paths = self._get_column_paths()
        column_paths += self.non_field_columns or tuple()
        return qs.only(*column_paths)

    def _prepare_row(self, row, fields):
        prepared_row = OrderedDict()
        for field in fields:
            if getattr(self, "show_display_fields", False) is True:
                prepared_row[field.display] = field.to_representation(row, self)
            else:
                prepared_row[
                    field.alias or field.column_path
                ] = field.to_representation(row, self)

        return prepared_row

    def preserialize(self, queryset=None):
        """
        Run any preparation here, for example, fetching and caching
        value lookups (value --> display)
        """
        pass

    @property
    def data(self):
        if self.queryset is None:
            return []

        fields = self.get_fields()
        qs = self._get_prepared_queryset(self.queryset)
        self.preserialize(qs)
        for row in qs:
            yield self._prepare_row(row, fields)

    def get_serialized_data(self, *args, **kwargs):
        return self.data
