from django.db.models import Q

from ..models import Tag
from ..permissions import UnauthenticatedReadOnlyPermission
from .base import BaseAPIFilterSet, BaseAPISerializer, BaseApiViewSet


class ProjectTagSerializer(BaseAPISerializer):
    class Meta:
        model = Tag
        exclude = []


class ProjectTagFilterSet(BaseAPIFilterSet):
    class Meta:
        model = Tag
        fields = ["name", "status"]


class ProjectTagViewSet(BaseApiViewSet):
    method_authentication_classes = {"GET": []}
    permission_classes = [UnauthenticatedReadOnlyPermission]
    filterset_class = ProjectTagFilterSet
    serializer_class = ProjectTagSerializer
    queryset = (
        Tag.objects.filter(
            Q(
                tagged_items__content_type__app_label="api",
                tagged_items__content_type__model="project",
            )
            | Q(tagged_items__isnull=True)
        )
        .distinct()
        .order_by("name")
    )
