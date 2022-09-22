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


# This /health/ endpoint bypasses all other middleware. This is required
# to allow the Application Load Balancer (ALB) to determine health on the
# targets in the Target Group
class HealthEndpointMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if request.META["PATH_INFO"] == "/health/":
            return HttpResponse("OK")
