from django.core.exceptions import ObjectDoesNotExist
from rest_framework import permissions
from rest_framework.exceptions import NotFound, PermissionDenied
from .exceptions import check_uuid
from .models import CollectRecord, Project, ProjectProfile
from .models.base import PROPOSED


class AuthenticatedReadOnlyPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return user.is_authenticated and request.method in permissions.SAFE_METHODS


class DefaultPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        return False


class UnauthenticatedReadOnlyPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.method in permissions.SAFE_METHODS


def get_project(pk):
    try:
        return Project.objects.get(pk=check_uuid(pk))
    except Project.DoesNotExist:
        raise NotFound("Not found: project %s" % pk)


def get_project_profile(project, profile):
    try:
        return ProjectProfile.objects.get(project=project, profile=profile)
    except ProjectProfile.DoesNotExist:
        raise PermissionDenied("You are not part of this project.")


def data_policy_permission(request, view, project_policy):
    if request.method not in permissions.SAFE_METHODS or not hasattr(
            view, "project_policy"
    ):
        return False

    pk = get_project_pk(request, view)
    project = get_project(pk)

    policy = getattr(project, view.project_policy, None)
    if policy and policy >= project_policy:
        return True
    return False


# get the project pk for use in determining
# user permissions for project-related data
def get_project_pk(request, view):
    data = request.data or {}
    kwargs = view.kwargs or {}

    pk = None
    if "project_pk" in kwargs:  # project pk from nested drf url
        pk = kwargs["project_pk"]
    elif "pk" in kwargs:  # project pk from project endpoint itself
        pk = kwargs["pk"]
    # project pk from attribute of data submitted.
    # Don't let users submit data related to another project.
    if "project" in data:
        pk = data["project"]
    return pk


class ProjectDataPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not user.is_authenticated:
            return False
        pk = get_project_pk(request, view)

        project = get_project(pk)
        pp = get_project_profile(project, user.profile)
        return True


class ProjectDataReadOnlyPermission(ProjectDataPermission):
    def has_permission(self, request, view):
        permission_check = super(ProjectDataReadOnlyPermission, self).has_permission(
            request, view
        )
        return permission_check is True and request.method in permissions.SAFE_METHODS


class ProjectDataCollectorPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not user.is_authenticated:
            return False
        if request.method == "DELETE":
            return False
        pk = get_project_pk(request, view)

        project = get_project(pk)
        pp = get_project_profile(project, user.profile)
        if project.is_open:
            return pp.is_collector
        else:
            return request.method in permissions.SAFE_METHODS


class ProjectDataAdminPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not user.is_authenticated:
            return False
        pk = get_project_pk(request, view)

        project = get_project(pk)
        pp = get_project_profile(project, user.profile)
        return pp.is_admin


class AttributeAuthenticatedUserPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not user.is_authenticated:
            return False

        if request.method in permissions.SAFE_METHODS or request.method == "POST":
            return True
        elif request.method in ("DELETE", "PUT"):
            pk = check_uuid(view.kwargs.get("pk"))
            try:
                qs = view.get_queryset()
                return qs.get(id=pk).status == PROPOSED
            except ObjectDoesNotExist:
                pass
        return False


class ProjectPublicPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        return data_policy_permission(request, view, Project.PUBLIC)


class ProjectPublicSummaryPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        return data_policy_permission(request, view, Project.PUBLIC_SUMMARY)


class CollectRecordOwner(permissions.BasePermission):
    def has_permission(self, request, view):
        record_ids = request.data.get("ids") or []
        pk = view.kwargs.get("pk")
        if pk:
            record_ids = [pk]
        elif not record_ids:
            return True

        profile = getattr(request.user, "profile")
        count = CollectRecord.objects.filter(id__in=record_ids, profile=profile).count()
        return count == len(record_ids)