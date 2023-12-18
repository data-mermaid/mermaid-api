from django.conf import settings
from django.conf.urls import include, re_path
from django.contrib import admin
from django.urls import path
from rest_framework.schemas import get_schema_view

from api.urls import api_urls

admin.autodiscover()


urlpatterns = [
    re_path(r"^v1/", include(api_urls), name="api-root"),
    path("admin/", admin.site.urls),
    path(
        "openapi/",
        get_schema_view(title="MERMAID API", description=""),
        name="openapi-schema",
    ),
]

urlpatterns += [path("api-auth/", include("rest_framework.urls", namespace="rest_framework"))]

if settings.ENVIRONMENT in ("local",):
    import debug_toolbar

    urlpatterns = [path("__debug__/", include(debug_toolbar.urls))] + urlpatterns
