from django.db import transaction
from django.db.models import Count, OuterRef, Subquery
from django.db.models.functions import Coalesce
from rest_framework import permissions, serializers
from rest_framework.exceptions import PermissionDenied, ValidationError

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
        # Annotated by ProjectProfileViewSet; count() for other instances.
        count = getattr(obj, "collect_records_count", None)
        if count is None:
            count = CollectRecord.objects.filter(
                profile_id=obj.profile_id, project_id=obj.project_id
            ).count()
        return count


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
    queryset = (
        ProjectProfile.objects.select_related("profile")
        .prefetch_related("profile__authusers")
        .annotate(
            collect_records_count=Coalesce(
                Subquery(
                    CollectRecord.objects.filter(
                        profile_id=OuterRef("profile_id"), project_id=OuterRef("project_id")
                    )
                    .order_by()
                    .values("profile_id")
                    .annotate(count=Count("id"))
                    .values("count")
                ),
                0,
            )
        )
    )
    permission_classes = [
        ProjectDataReadOnlyPermission
        | ProjectProfileCollectorPermission
        | ProjectDataAdminPermission
    ]
    filterset_class = ProjectProfileFilterSet

    def perform_update(self, serializer):
        instance = serializer.instance
        new_role = serializer.validated_data.get("role", instance.role)
        old_ids = (instance.profile_id, instance.project_id)
        with transaction.atomic():
            if new_role != ProjectProfile.ADMIN and instance.is_last_admin(for_update=True):
                raise ValidationError(
                    "You are the last admin of this project! Create another admin before you relinquish."
                )
            serializer.save()
        # Annotated count is stale if the member's profile/project changed.
        if (instance.profile_id, instance.project_id) != old_ids:
            instance.__dict__.pop("collect_records_count", None)

    def perform_destroy(self, instance):
        # ProjectProfileCollectorPermission lets a COLLECTOR reach DELETE, but a
        # collector may only remove their own membership (leave the project).
        # Removing another member is an admin action (card 2239).
        user_profile = self.request.user.profile
        acting_pp = get_project_profile(instance.project, user_profile, request=self.request)
        is_admin = acting_pp is not None and acting_pp.is_admin
        if not is_admin and instance.profile_id != getattr(user_profile, "pk", None):
            raise PermissionDenied("Only a project admin can remove another member.")

        with transaction.atomic():
            if instance.is_last_admin(for_update=True):
                raise ValidationError(
                    "You are the last admin of this project! Create another admin before you relinquish."
                )
            instance.updated_by = self._set_updated_by(self.request)
            instance.delete()
