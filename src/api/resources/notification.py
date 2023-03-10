from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ..models import Notification
from .base import BaseAPIFilterSet, BaseAPISerializer, BaseApiViewSet


class NotificationSerializer(BaseAPISerializer):
    class Meta:
        model = Notification
        fields = "__all__"


class NotificationFilterSet(BaseAPIFilterSet):
    class Meta:
        model = Notification
        fields = ["owner"]


class NotificationViewSet(BaseApiViewSet):
    serializer_class = NotificationSerializer
    model = Notification
    filterset_class = NotificationFilterSet
    permission_classes = [IsAuthenticated]

    http_method_names = ["get", "head", "delete"]

    def get_queryset(self):
        user = self.request.user
        profile = user.profile
        if profile is None:
            return Notification.objects.none()
        return Notification.objects.filter(owner=profile).order_by("-created_on")

    @action(detail=False, methods=["delete"])
    def delete_all(self, request):
        deleted_count, deleted_objects = self.get_queryset().delete()
        label = "notification"
        if deleted_count != 1:
            label = "notifications"
        return Response(f"deleted {deleted_count} {label}")
