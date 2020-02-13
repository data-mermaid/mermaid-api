from django.conf.urls import url, include
from api.urls import api_urls
from django.conf import settings
from django.contrib import admin
from django.urls import path
from rest_framework.schemas import get_schema_view

admin.autodiscover()


urlpatterns = [
    url(r'^v1/', include(api_urls), name='api-root'),
    path('admin/', admin.site.urls),
    path('openapi/', get_schema_view(
        title="MERMAID API",
        description=""
    ), name='openapi-schema')
]


urlpatterns += [
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
]
