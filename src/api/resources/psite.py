from ..models import Site
from .base import BaseAPIFilterSet, BaseAPISerializer, BaseProjectApiViewSet
from .mixins import CopyRecordsMixin, CreateOrUpdateSerializerMixin, ProtectedResourceMixin
from ..notifications import notify_cr_owners_site_mr_deleted


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

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        deleted_by = getattr(request.user, "profile", None)
        response = super().destroy(request, *args, **kwargs)
        notify_cr_owners_site_mr_deleted(instance, deleted_by)
        return response
