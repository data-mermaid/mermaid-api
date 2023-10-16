from functools import cache
from django_filters import rest_framework as filters

from ..models import Covariate, Site
from .base import BaseAPIFilterSet, BaseAPISerializer, BaseProjectApiViewSet, PointFieldValidated
from .mixins import CopyRecordsMixin, CreateOrUpdateSerializerMixin, NotifyDeletedSiteMRMixin


class PSiteSerializer(CreateOrUpdateSerializerMixin, BaseAPISerializer):
    location = PointFieldValidated()

    class Meta:
        geo_field = "location"
        model = Site
        exclude = []
    
    @cache
    def _covariates(self, project_id):
        covariates = {}
        for c in Covariate.objects.filter(site__project_id=project_id):
            site_id = str(c.site_id)
            if site_id not in covariates:
                covariates[site_id] = []
            covariates[site_id].append({"id": str(c.id), "name": c.name, "value": c.value, "requested_datestamp": c.requested_datestamp})

        return covariates

    def to_representation(self, instance):
        request = self.context.get("request")

        if request and request.query_params.get("covars"):
            representation = super().to_representation(instance)
            project_id = str(instance.project_id)
            site_id = str(instance.id)
            representation["covariates"] = self._covariates(project_id).get(site_id) or {}

            return representation

        return super().to_representation(instance)


class PSiteFilterSet(BaseAPIFilterSet):
    covars = filters.BooleanFilter(
        field_name="covars",
        method="filter_covars"
    )

    def filter_covars(self, queryset, name, value):
        return queryset

    class Meta:
        model = Site
        fields = ["country", "reef_type", "reef_zone", "exposure", "covars"]
    

class PSiteViewSet(NotifyDeletedSiteMRMixin, CopyRecordsMixin, BaseProjectApiViewSet):
    model_display_name = "Site"
    serializer_class = PSiteSerializer
    queryset = Site.objects.all()
    project_lookup = "project"
    filterset_class = PSiteFilterSet
    search_fields = ["name"]
