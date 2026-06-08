from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path, re_path
from rest_framework.schemas import get_schema_view

from api.urls import api_urls

admin.autodiscover()


urlpatterns = [
    re_path(r"^v1/", include(api_urls), name="api-root"),
    path(
        "admin/password_reset/", auth_views.PasswordResetView.as_view(), name="admin_password_reset"
    ),
    path(
        "admin/password_reset/done/",
        auth_views.PasswordResetDoneView.as_view(),
        name="password_reset_done",
    ),
    path(
        "admin/reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),
    path(
        "admin/reset/done/",
        auth_views.PasswordResetCompleteView.as_view(),
        name="password_reset_complete",
    ),
    path("admin/", admin.site.urls),
    path(
        "openapi/",
        get_schema_view(title="MERMAID API", description=""),
        name="openapi-schema",
    ),
]

urlpatterns += [path("api-auth/", include("rest_framework.urls", namespace="rest_framework"))]

if settings.ENVIRONMENT in ("local",):
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
