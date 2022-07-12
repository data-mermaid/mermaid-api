from django.conf import settings
from django.http import HttpResponse
from django.utils.deprecation import MiddlewareMixin


class APIVersionMiddleware(MiddlewareMixin):
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response.setdefault("HTTP_API_VERSION", settings.API_VERSION)

        return response


# This is not working as expected. Still returns "ok", not "OK",
# so it seems to be getting to the endpoint.
class HealthEndpointMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if request.META["PATH_INFO"] == "/health/":
            return HttpResponse("OK")
