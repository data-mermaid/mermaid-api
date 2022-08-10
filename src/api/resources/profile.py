import django_filters
from rest_framework.exceptions import MethodNotAllowed
from .base import BaseAPIFilterSet, BaseApiViewSet, BaseAPISerializer
from ..models import Profile
from ..permissions import *


class ProfileSerializer(BaseAPISerializer):
    class Meta:
        model = Profile
        fields = ["id", "created_on", "updated_on", "updated_by"]


class ProfileFilterSet(BaseAPIFilterSet):
    organization = django_filters.UUIDFilter(
        field_name="projects__project__tagged_items__tag_id",
        distinct=True,
        label="Associated with organization associated with at least one project "
        "associated with profile",
    )
    project = django_filters.UUIDFilter(
        field_name="projects__project", distinct=True, label="Associated with project"
    )
    email = django_filters.CharFilter(lookup_expr='iexact')

    class Meta:
        model = Profile
        fields = ["organization", "project", "email"]


class ProfileViewSet(BaseApiViewSet):
    serializer_class = ProfileSerializer
    queryset = Profile.objects.all()
    permission_classes = [UnauthenticatedReadOnlyPermission]
    filter_class = ProfileFilterSet
    search_fields = ['^email', '^first_name', '^last_name', ]

    def create(self, request):
        raise MethodNotAllowed("POST")

    def update(self, request, pk=None):
        raise MethodNotAllowed("PUT")

    def partial_update(self, request, pk=None):
        raise MethodNotAllowed("PATCH")

    def destroy(self, request, pk=None):
        raise MethodNotAllowed("DELETE")
