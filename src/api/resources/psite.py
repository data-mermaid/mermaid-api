from ..models import Site
from .base import BaseAPIFilterSet, BaseAPISerializer, BaseProjectApiViewSet
from .mixins import CopyRecordsMixin, CreateOrUpdateSerializerMixin, ProtectedResourceMixin


class PSiteSerializer(CreateOrUpdateSerializerMixin, BaseAPISerializer):
    class Meta:
        geo_field = "location"
        model = Site
        exclude = []


class PSiteFilterSet(BaseAPIFilterSet):
    class Meta:
        model = Site
        fields = ["country", "reef_type", "reef_zone", "exposure"]


class PSiteViewSet(ProtectedResourceMixin, CopyRecordsMixin, BaseProjectApiViewSet):
    model_display_name = "Site"
    serializer_class = PSiteSerializer
    queryset = Site.objects.all()
    project_lookup = "project"
    filterset_class = PSiteFilterSet
    search_fields = ["name"]
