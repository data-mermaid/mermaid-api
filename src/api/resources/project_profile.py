from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_condition import Or
from .base import BaseAPIFilterSet, BaseProjectApiViewSet, BaseAPISerializer
from ..models import ProjectProfile
from ..permissions import *


class ProjectProfileSerializer(BaseAPISerializer):
    profile_name = serializers.ReadOnlyField()
    is_collector = serializers.ReadOnlyField()
    is_admin = serializers.ReadOnlyField()

    class Meta:
        model = ProjectProfile
        exclude = []


class ProjectProfileFilterSet(BaseAPIFilterSet):

    class Meta:
        model = ProjectProfile
        fields = ['project', 'profile', 'role', ]


class ProjectProfileCollectorPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not user.is_authenticated:
            return False
        if request.method != 'DELETE':
            return False
        pk = get_project_pk(request, view)

        project = get_project(pk)
        pp = get_project_profile(project, user.profile)
        return project.is_open and pp.is_collector


class ProjectProfileViewSet(BaseProjectApiViewSet):
    serializer_class = ProjectProfileSerializer
    queryset = ProjectProfile.objects.all()
    permission_classes = [
        Or(ProjectDataReadOnlyPermission,
           ProjectProfileCollectorPermission,
           ProjectDataAdminPermission)
    ]
    filter_class = ProjectProfileFilterSet

    def is_last_admin(self):
        obj = self.get_object()
        existing_project = obj.project
        admin_profiles = ProjectProfile.objects.filter(project=existing_project,
                                                       role=ProjectProfile.ADMIN)
        return admin_profiles.count() < 2 and obj.pk == admin_profiles[0].pk

    def perform_update(self, serializer):
        if self.is_last_admin():
            raise ValidationError('You are the last admin of this project! Create another admin before you relinquish.')
        serializer.save()

    def perform_destroy(self, instance):
        if self.is_last_admin():
            raise ValidationError('You are the last admin of this project! Create another admin before you relinquish.')
        instance.delete()
