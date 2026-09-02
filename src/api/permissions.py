import uuid
from collections.abc import Callable
from typing import Any

from django.core.exceptions import ObjectDoesNotExist
from rest_framework import permissions
from rest_framework.exceptions import NotFound, ParseError
from rest_framework.request import Request

from .exceptions import check_uuid
from .models import APIKey, CollectRecord, Project, ProjectProfile
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


PROJECT_CACHE_ATTR = "_project_cache"
PROJECT_PROFILE_CACHE_ATTR = "_project_profile_cache"
# Request-scoped memoization cache attrs used by get_project/get_project_profile.
# Shared by sync/utils.create_view_request (to propagate the caches onto
# derived ViewRequests) and sync/views._invalidate_project_caches (to clear
# them after a write) - import from here rather than re-declaring the names.
REQUEST_CACHE_ATTRS = (PROJECT_CACHE_ATTR, PROJECT_PROFILE_CACHE_ATTR)


def cached_lookup(
    request: Request | None, cache_attr: str, key: Any, loader: Callable[[], Any]
) -> Any:
    """Fetch `key` via `loader()`, memoizing on a dict stored as `cache_attr`
    on `request`. The dict is created lazily on `request` itself on first use
    (and shared with any derived request objects that copy the attribute
    reference, see sync/utils.create_view_request), so repeated permission
    checks against the same request object avoid re-running `loader` for the
    same key."""
    if request is None:
        return loader()

    cache = getattr(request, cache_attr, None)
    if cache is None:
        cache = {}
        setattr(request, cache_attr, cache)
    elif key in cache:
        return cache[key]

    value = loader()
    cache[key] = value
    return value


def get_project(pk, request=None):
    pk = check_uuid(pk)
    cache_key = uuid.UUID(str(pk))

    def _load():
        try:
            return Project.objects.get(pk=pk)
        except Project.DoesNotExist:
            raise NotFound("Not found: project %s" % pk)

    return cached_lookup(request, PROJECT_CACHE_ATTR, cache_key, _load)


def get_request_api_key(request):
    """The APIKey that authenticated `request`, or None for any other caller.

    `request.auth` is the JWT string for an Auth0 caller and None for an
    anonymous one, so the isinstance check is what separates a key-authenticated
    request from every other kind.

    A key grants exactly its profile's access, so nothing in the permission
    classes needs this to decide yes or no. It is here for the callers that
    care *how* a request was authenticated rather than as whom: attributing a
    write (resources/base.get_request_profile) and refusing to let a key mint
    another key.
    """
    if request is None:
        return None
    api_key = getattr(request, "auth", None)
    return api_key if isinstance(api_key, APIKey) else None


def get_project_profile(project, profile, request=None):
    """Like ProjectProfile.objects.get_or_none(project=project, profile=profile),
    but memoized per-request (see cached_lookup) since permission classes
    commonly look up the same (project, profile) pair multiple times per
    request."""
    if project is None or profile is None:
        return None

    return cached_lookup(
        request,
        PROJECT_PROFILE_CACHE_ATTR,
        (project.pk, profile.pk),
        lambda: ProjectProfile.objects.get_or_none(project=project, profile=profile),
    )


def invalidate_project(request, pk):
    """Drop the cached Project for `pk` (see get_project) so a later lookup
    re-fetches it instead of reusing a pre-write instance - e.g. after a
    sync push writes a project's own fields."""
    cache = getattr(request, PROJECT_CACHE_ATTR, None)
    if cache is None:
        return
    try:
        cache_key = uuid.UUID(str(check_uuid(pk)))
    except ParseError:
        return
    cache.pop(cache_key, None)


def invalidate_project_profile(request, project_pk, profile):
    """Drop the cached ProjectProfile for (project_pk, profile) (see
    get_project_profile) so a later lookup re-fetches it - e.g. after a sync
    push writes a profile's own role. `profile` must be a real model
    instance: get_project_profile is only ever looked up by
    request.user.profile, never a record's own "profile" field."""
    cache = getattr(request, PROJECT_PROFILE_CACHE_ATTR, None)
    if cache is None or profile is None:
        return
    try:
        project_uuid = uuid.UUID(str(project_pk))
    except ValueError:
        return
    cache.pop((project_uuid, profile.pk), None)


def data_policy_permission(request, view, project_policy):
    if request.method not in permissions.SAFE_METHODS or not hasattr(view, "project_policy"):
        return False

    pk = get_project_pk(request, view)
    project = get_project(pk, request=request)

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

        project = get_project(pk, request=request)
        pp = get_project_profile(project, user.profile, request=request)
        if pp is None:
            return False
        return True


class ProjectDataReadOnlyPermission(ProjectDataPermission):
    def has_permission(self, request, view):
        permission_check = super().has_permission(request, view)
        return permission_check is True and request.method in permissions.SAFE_METHODS


class ProjectDataCollectorPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not user.is_authenticated:
            return False
        if request.method == "DELETE":
            return False
        pk = get_project_pk(request, view)

        project = get_project(pk, request=request)
        pp = get_project_profile(project, user.profile, request=request)
        if pp is None:
            return False
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

        project = get_project(pk, request=request)
        pp = get_project_profile(project, user.profile, request=request)
        if pp is None:
            return False
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
        record_ids = request.data.get("ids") or request.data.get("collect_record_id") or []
        if isinstance(record_ids, str):
            record_ids = [record_ids]
        elif "pk" in view.kwargs and view.kwargs["pk"]:
            record_ids = [view.kwargs["pk"]]
        elif not record_ids:
            return True

        for record_id in record_ids:
            check_uuid(record_id)

        profile = getattr(request.user, "profile")
        count = CollectRecord.objects.filter(id__in=record_ids, profile=profile).count()
        return count == len(record_ids)
