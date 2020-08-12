

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
    __slots__ = ("method", "display")

    def __init__(self, display, method):
        self.display = display
        self.method = method

    def to_representation(self, row, serializer_instance):
        return self.method(self, row, serializer_instance)
