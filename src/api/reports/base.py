class BaseReport(object):
    def __init__(self, *args, **kwargs):
        pass

    @property
    def media_type(self):
        raise NotImplementedError()

    def stream(self, data, serializer_class, *args, **kwargs):
        raise NotImplementedError()

    def generate(self, path, data, serializer_class, *args, **kwargs):
        raise NotImplementedError()
