import json
import time
from datetime import datetime

from django.conf import settings
from django.http import HttpResponse
from django.utils.deprecation import MiddlewareMixin

from .utils.auth0utils import decode


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
            return HttpResponse(f"OK ({settings.ENVIRONMENT})")


class MetricsMiddleware:
    USER = "user"
    APP = "app"

    def __init__(self, get_response):
        self.get_response = get_response

    def parse_token(self, token):
        if token is None:
            return "", "", ""

        sub = (decode(token.split(" ")[1].strip()) or {}).get("sub")
        if "|" in sub:
            return (
                self.USER,
                *sub.split("|"),
            )
        elif "@" in sub:
            return (
                self.APP,
                *sub.split("@"),
            )

        return "", "", ""

    def _obfuscate(self, value):
        for key in value.keys():
            if key.lower() in ["password", "password1", "password2", "token"]:
                for i in range(len(value[key])):
                    value[key][i] = "********"

    def __call__(self, request):
        url_path = request.path
        method = request.method
        token_type, auth_type, user_id = self.parse_token(
            request.headers.get("Authorization")
        )

        s = time.time_ns()

        response = self.get_response(request)

        response_status_code = response.status_code
        duration = (time.time_ns() - s) / 1_000_000  # ms

        query_params = dict(request.GET)
        self._obfuscate(query_params)

        print(
            json.dumps(
                {
                    "type": "mermaid-metrics",
                    "timestamp": datetime.now().timestamp(),
                    "method": method,
                    "path": url_path,
                    "query_params": query_params,
                    "status_code": response_status_code,
                    "duration_ms": duration,
                    "token_type": token_type,
                    "auth_type": auth_type,
                    "user_id": user_id or "",
                }
            )
        )

        return response
