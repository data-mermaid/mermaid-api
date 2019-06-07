from base import BaseApiViewSet, BaseAPISerializer, BaseAPIFilterSet
from django.contrib.contenttypes.models import ContentType
from ..models import Tag
from ..permissions import UnauthenticatedReadOnlyPermission


class ProjectTagSerializer(BaseAPISerializer):

    class Meta:
        model = Tag
        exclude = []


class ProjectTagFilterSet(BaseAPIFilterSet):

    class Meta:
        model = Tag
        fields = ['name', 'status']


class ProjectTagViewSet(BaseApiViewSet):
    permission_classes = [UnauthenticatedReadOnlyPermission]
    filter_class = ProjectTagFilterSet
    serializer_class = ProjectTagSerializer
    pt = ContentType.objects.get(app_label="api", model="project")
    queryset = Tag.objects.filter(tagged_items__content_type_id=pt.pk).order_by('name')
