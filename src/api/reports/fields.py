class ReportField(object):
    def __init__(self, column_path, display=None, formatter=None, alias=None, **kwargs):
        self._display = None
        self.column_path = column_path
        self.display = display
        self.formatter = formatter
        self.alias = alias
        for key in kwargs:
            setattr(self, key, kwargs[key])

        if hasattr(self, "protocol") and hasattr(self, "key"):
            self.alias = f"{self.protocol}__{self.key}"

    @property
    def display(self):
        if self._display is None:
            return self.column_path

        return self._display

    @display.setter
    def display(self, value):
        self._display = value

    def to_representation(self, row, serializer_instance):
        value = getattr(row, self.column_path)
        if self.formatter is None:
            return value

        return self.formatter(value, self, row, serializer_instance)

    def __str__(self):
        return f"{self.column_path} - {self.display} ({self.alias})"
