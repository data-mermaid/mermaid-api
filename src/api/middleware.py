from django.conf import settings
from django.utils.deprecation import MiddlewareMixin


class APIVersionMiddleware(MiddlewareMixin):
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response.setdefault("HTTP_API_VERSION", settings.API_VERSION)

        return response
