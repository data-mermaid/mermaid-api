from rest_framework import status, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response

from ..models import ProfileAppSettings
from .base import BaseAPISerializer
from .me import AuthenticatedMePermission


class ProfileAppSettingsSerializer(BaseAPISerializer):
    class Meta:
        model = ProfileAppSettings
        fields = [
            "id",
            "demo_project_prompt_dismissed",
            "created_on",
            "updated_on",
        ]
        read_only_fields = ["id", "created_on", "updated_on"]


class ProfileAppSettingsViewSet(viewsets.ModelViewSet):
    serializer_class = ProfileAppSettingsSerializer
    permission_classes = [AuthenticatedMePermission]

    def get_queryset(self):
        return ProfileAppSettings.objects.filter(profile=self.request.user.profile)

    def create(self, request):
        settings, created = ProfileAppSettings.objects.get_or_create(profile=request.user.profile)
        serializer = self.serializer_class(settings)
        status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        return Response(serializer.data, status=status_code)

    def retrieve(self, request, pk=None):
        settings = get_object_or_404(self.get_queryset(), pk=pk)
        return Response(self.serializer_class(settings).data)

    def _update_settings(self, request, pk, partial):
        settings = get_object_or_404(self.get_queryset(), pk=pk)

        serializer = self.serializer_class(
            instance=settings, data=request.data, context={"request": request}, partial=partial
        )

        if not serializer.is_valid():
            raise ValidationError(serializer.errors)

        serializer.save()
        return Response(serializer.data)

    def update(self, request, pk=None):
        return self._update_settings(request, pk, partial=False)

    def partial_update(self, request, pk=None):
        return self._update_settings(request, pk, partial=True)

    def destroy(self, request, pk=None):
        settings = get_object_or_404(self.get_queryset(), pk=pk)
        settings.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
