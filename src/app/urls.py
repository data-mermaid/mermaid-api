from django.conf.urls import url, include
from api.urls import api_urls
from django.conf import settings
from django.contrib import admin
admin.autodiscover()


urlpatterns = [
    url(r'^v1/', include(api_urls), name='api-root'),
    url(r'^admin/', include(admin.site.urls)),
]


urlpatterns += [
    url(r'^api-auth/', include('rest_framework.urls',
                               namespace='rest_framework')),
    # url(r'^auth/', include('oauth2_package.urls')),
]
