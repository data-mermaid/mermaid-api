from collections import OrderedDict


def handle_none(default_val=None):

    def decorator(func):

        def wrapper(*args, **kwargs):
            if args[0] is None:
                return default_val

            return func(*args, **kwargs)

        return wrapper

    return decorator


@handle_none()
def to_unicode(value, field, row, serializer_instance):
    return str(value)


@handle_none()
def to_float(value, field, row, serializer_instance):
    return float(value)


@handle_none()
def to_latitude(value, field, row, serializer_instance):
    return value.y


@handle_none()
def to_longitude(value, field, row, serializer_instance):
    return value.x


class ReportField(object):
    __slots__ = ("column_path", "formatter", "_display")

    def __init__(self, column_path, display=None, formatter=None):
        self._display = None
        self.column_path = column_path
        self.display = display
        self.formatter = formatter

    @property
    def display(self):
        if self._display is None:
            return self.column_path

        return self._display

    @display.setter
    def display(self, value):
        self._display = value

    def to_representation(self, row, serializer_instance):
        value = row.get(self.column_path)
        if self.formatter is None:
            return value

        return self.formatter(value, self, row, serializer_instance)


class ReportMethodField(object):
    __slots__ = ("formatter", "display")

    def __init__(self, display, formatter):
        self.display = display
        self.formatter = formatter

    def to_representation(self, row, serializer_instance):
        return self.formatter(self, row, serializer_instance)


class ReportSerializer(object):
    fields = None
    non_field_columns = None

    def __init__(self, queryset, ignore_select_related=False):
        self.queryset = queryset
        self.ignore_select_related = ignore_select_related

    @classmethod
    def get_fields(cls):
        if cls.fields is None:
            raise ValueError("fields not defined")

        return cls.fields

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
        pass

    @property
    def data(self):
        fields = self.get_fields()
        qs = self._get_prepared_queryset(self.queryset)
        self.preserialize(qs)
        for row in qs:
            yield self._prepare_row(row, fields)
