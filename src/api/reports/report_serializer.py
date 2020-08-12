import re
from collections import OrderedDict
from operator import itemgetter

from ..utils import is_match

from api.utils.timer import Timer


class ReportSerializer(object):
    fields = None
    non_field_columns = None

    def __init__(self, queryset, ignore_select_related=False):
        self.queryset = queryset
        self.ignore_select_related = ignore_select_related
        self.cache = dict()

    @classmethod
    def get_fields(cls):
        if cls.fields is None:
            raise ValueError("fields not defined")

        fields = cls.fields
        if hasattr(cls, "excluded_fields"):
            patterns = [re.compile(c) for c in cls.excluded_fields]
            return [c for c in fields
                    if is_match(c.display, patterns) is False]
        return fields

    def _get_column_paths(self):
        return [f.column_path for f in self.get_fields() if hasattr(f, "column_path")]

    def _get_prepared_queryset(self, qs):
        if self.ignore_select_related is False:
            qs = qs.select_related()

        column_paths = self._get_column_paths()
        column_paths += self.non_field_columns or tuple()
        return qs.values(*column_paths)

    def _prepare_row(self, row, fields):
        prepared_row = OrderedDict()
        for field in fields:
            prepared_row[field.display] = field.to_representation(row, self)
        return prepared_row

    def preserialize(self, queryset=None):
        """
        Run any preparation here, for example, fetching and caching
        value lookups (value --> display)
        """
        pass

    @property
    def data(self):
        fields = self.get_fields()
        qs = self._get_prepared_queryset(self.queryset)
        self.preserialize(qs)
        for row in qs:
            yield self._prepare_row(row, fields)

    def get_serialized_data(self, *args, **kwargs):
        serialized_data = self.data
        if 'order_by' in kwargs:
            serialized_data = sorted(serialized_data, key=itemgetter(*kwargs['order_by']))
        return serialized_data
