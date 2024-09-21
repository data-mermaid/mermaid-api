
class BaseReportField:
    def __init__(self, display=None, alias=None, **kwargs):
        self._display = None
        self.display = display
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
        raise NotImplementedError()

    def __str__(self):
        return f"{self.display} ({self.alias})"


class ReportField(BaseReportField):
    def __init__(self, column_path, display=None, formatter=None, alias=None, **kwargs):
        super().__init__(display=display, alias=alias, **kwargs)
        self.column_path = column_path
        self.formatter = formatter

    def to_representation(self, row, serializer_instance):
        value = getattr(row, self.column_path)
        if self.formatter is None:
            return value

        return self.formatter(value, self, row, serializer_instance)


class ReportMethodField(BaseReportField):
    def __init__(self, method_name, display=None, alias=None, **kwargs):
        super().__init__(display=display, alias=alias, **kwargs)
        self.method_name = method_name

    def to_representation(self, row, serializer_instance):
        if not hasattr(serializer_instance, self.method_name):
            raise AttributeError(f"Method {self.method_name} does not exist on serializer_instance")

        method = getattr(serializer_instance, self.method_name)
        return method(row)
