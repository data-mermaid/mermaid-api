from django.test import RequestFactory

from api.middleware import HealthEndpointMiddleware


def test_health_endpoint_short_circuits():
    request = RequestFactory().get("/health/")

    def get_response(_request):
        raise AssertionError("get_response should not be called for /health/")

    response = HealthEndpointMiddleware(get_response=get_response)(request)

    assert response.status_code == 200
    assert response.content.startswith(b"OK")


def test_non_health_endpoint_passes_through():
    request = RequestFactory().get("/other/")
    sentinel = object()

    response = HealthEndpointMiddleware(get_response=lambda r: sentinel)(request)

    assert response is sentinel
