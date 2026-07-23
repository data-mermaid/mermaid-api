from django.db import transaction
from rest_framework import permissions, serializers
from rest_framework.exceptions import ValidationError

from ..models import CollectRecord, ProjectProfile
from ..permissions import (
    ProjectDataAdminPermission,
    ProjectDataReadOnlyPermission,
    get_project,
    get_project_pk,
    get_project_profile,
)
from .base import BaseAPIFilterSet, BaseAPISerializer, BaseProjectApiViewSet


class ProjectProfileSerializer(BaseAPISerializer):
    profile_name = serializers.ReadOnlyField()
    is_collector = serializers.ReadOnlyField()
    is_admin = serializers.ReadOnlyField()
    email = serializers.ReadOnlyField(source="profile.email")
    num_active_sample_units = serializers.SerializerMethodField()
    picture = serializers.ReadOnlyField(source="profile.picture_url")
    num_account_connections = serializers.ReadOnlyField(source="profile.num_account_connections")

    class Meta:
        model = ProjectProfile
        exclude = []

    def get_num_active_sample_units(self, obj):
        return CollectRecord.objects.filter(profile=obj.profile, project=obj.project).count()


class ProjectProfileFilterSet(BaseAPIFilterSet):
    class Meta:
        model = ProjectProfile
        fields = [
            "project",
            "profile",
            "role",
        ]


class ProjectProfileCollectorPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not user.is_authenticated:
            return False
        if request.method != "DELETE":
            return False
        pk = get_project_pk(request, view)

        project = get_project(pk, request=request)
        pp = get_project_profile(project, user.profile, request=request)
        if pp is None:
            return False
        return project.is_open and pp.is_collector


class ProjectProfileViewSet(BaseProjectApiViewSet):
    serializer_class = ProjectProfileSerializer
    queryset = ProjectProfile.objects.all()
    permission_classes = [
        ProjectDataReadOnlyPermission
        | ProjectProfileCollectorPermission
        | ProjectDataAdminPermission
    ]
    filterset_class = ProjectProfileFilterSet

    def perform_update(self, serializer):
        instance = serializer.instance
        new_role = serializer.validated_data.get("role", instance.role)
        with transaction.atomic():
            if new_role != ProjectProfile.ADMIN and instance.is_last_admin(for_update=True):
                raise ValidationError(
                    "You are the last admin of this project! Create another admin before you relinquish."
                )
            serializer.save()

    def perform_destroy(self, instance):
        with transaction.atomic():
            if instance.is_last_admin(for_update=True):
                raise ValidationError(
                    "You are the last admin of this project! Create another admin before you relinquish."
                )
            instance.updated_by = self._set_updated_by(self.request)
            instance.delete()
