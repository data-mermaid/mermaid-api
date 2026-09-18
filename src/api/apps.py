from django.apps import AppConfig


class ApiConfig(AppConfig):
    name = "api"

    def ready(self):
        from . import checks  # noqa: F401
        from . import patches  # noqa: F401
        from . import signals  # noqa: F401
