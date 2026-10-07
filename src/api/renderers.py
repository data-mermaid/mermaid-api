from django.conf import settings
from rest_framework.renderers import BrowsableAPIRenderer


class BaseBrowsableAPIRenderer(BrowsableAPIRenderer):
    media_type = "text/html"
    format = ".api"
    charset = "utf-8"

    def get_context(self, data, accepted_media_type, renderer_context):
        context = super().get_context(data, accepted_media_type, renderer_context)
        context["nav_name"] = f"{settings.PROJECT_NAME} [{settings.ENVIRONMENT}]"

        return context
