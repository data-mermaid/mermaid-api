import django_filters
from django.conf import settings
from rest_framework import exceptions, permissions, serializers, viewsets

from ..models import AppVersion
from ..utils.auth0utils import decode_hs


class AppVersionSerializer(serializers.ModelSerializer):

    class Meta:
        model = AppVersion
        fields = ['id', 'application', 'version']


class AppVersionPermission(permissions.BasePermission):

    def has_permission(self, request, view):
        write_methods = ('PUT', 'POST',)
        user = request.user
        method = request.method
        if not user and not user.is_authenticated:
            return False

        if method in permissions.SAFE_METHODS:
            return True

        if method not in write_methods:
            return False

        try:
            jwt = decode_hs(request.auth)
            client_id = jwt.get('azp')
            return client_id == settings.CIRCLE_CI_CLIENT_ID

        except exceptions.AuthenticationFailed:
            return False


class AppVersionViewSet(viewsets.ModelViewSet):
    serializer_class = AppVersionSerializer
    queryset = AppVersion.objects.all()
    filter_backends = (django_filters.rest_framework.DjangoFilterBackend,)
    filter_fields = ('application',)
    permission_classes = [AppVersionPermission]
