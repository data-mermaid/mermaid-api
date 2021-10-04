import django_filters
from rest_framework import serializers

from .base import (
    BaseAPIFilterSet,
    BaseApiViewSet,
    BaseAPISerializer,
    ExtendedSerializer,
    ModelNameReadOnlyField,
    ListFilter,
)
from .mixins import ProtectedResourceMixin
from ..models import Site, Project
from ..permissions import AuthenticatedReadOnlyPermission


class SiteExtendedSerializer(ExtendedSerializer):
    project = ModelNameReadOnlyField()
    country = ModelNameReadOnlyField()
    reef_type = ModelNameReadOnlyField()
    reef_zone = ModelNameReadOnlyField()
    exposure = ModelNameReadOnlyField()
    latitude = serializers.SerializerMethodField()
    longitude = serializers.SerializerMethodField()

    class Meta:
        geo_field = 'location'
        model = Site
        exclude = []

    def get_latitude(self, obj):
        if obj.location is not None:
            return obj.location.y
        return None

    def get_longitude(self, obj):
        if obj.location is not None:
            return obj.location.x
        return None


class SiteSerializer(BaseAPISerializer):
    country_name = serializers.SerializerMethodField()
    project_name = serializers.SerializerMethodField()
    reef_type_name = serializers.SerializerMethodField()
    reef_zone_name = serializers.SerializerMethodField()
    exposure_name = serializers.SerializerMethodField()

    class Meta:
        geo_field = 'location'
        model = Site
        available_fields = [
            'country_name',
            'project_name',
            'reef_type_name',
            'reef_zone_name',
            'exposure_name',
        ]
        exclude = []

    def get_country_name(self, obj):
        return obj.country.name

    def get_project_name(self, obj):
        return obj.project.name

    def get_reef_type_name(self, obj):
        return obj.reef_type.name

    def get_reef_zone_name(self, obj):
        return obj.reef_zone.name

    def get_exposure_name(self, obj):
        return obj.exposure.name


class SiteFilterSet(BaseAPIFilterSet):
    project = django_filters.UUIDFilter(field_name='project', distinct=True,
                                        label='Associated with project')

    country_id = ListFilter()
    unique = django_filters.CharFilter(method='filter_unique')
    exclude_projects = django_filters.CharFilter(method='filter_not_projects')

    class Meta:
        model = Site
        fields = [
            'project',
            'country',
            'reef_type',
            'reef_zone',
            'exposure',
            'exclude_projects',
        ]

    def filter_unique(self, queryset, name, value):
        unique_fields = (
            'name',
            'country_id',
            'reef_type_id',
            'reef_zone_id',
            'exposure_id',
            'location'
        )
        project_id = value

        group_by = ','.join(['"{}"'.format(uf) for uf in unique_fields])

        sql = """
            "site".id::text IN (
                SELECT id
                FROM (
                    SELECT (agg_sites.ids)[1] AS id, project_ids
                    FROM
                    (
                        SELECT
                            ARRAY_AGG(id::text) AS ids,
                            ARRAY_AGG(project_id::text) AS project_ids
                        FROM site
                        GROUP BY {}
                    ) AS agg_sites
                    WHERE
                        NOT('{}' = ANY(agg_sites.project_ids))
                ) AS site_ids
            )
        """.format(group_by, project_id)

        return queryset.extra(where=[sql])

    def filter_not_projects(self, queryset, name, value):
        value_list = [v.strip() for v in value.split(u',')]
        return queryset.exclude(project__in=value_list)


class SiteViewSet(ProtectedResourceMixin, BaseApiViewSet):
    model_display_name = "Site"
    serializer_class = SiteSerializer
    queryset = Site.objects.exclude(project__status=Project.TEST)
    permission_classes = [AuthenticatedReadOnlyPermission]
    filter_class = SiteFilterSet
    search_fields = ['$name', '$project__name', '$country__name',]
