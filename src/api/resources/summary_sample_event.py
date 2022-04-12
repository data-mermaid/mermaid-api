from django.db.models import Q, CharField
from django_filters import rest_framework as filters
from .base import (
    BaseViewAPIGeoSerializer,
    BaseViewAPISerializer,
    AggregatedViewFilterSet,
)
from .sample_units import AggregatedViewMixin, BaseApiViewSet
from ..permissions import UnauthenticatedReadOnlyPermission
from ..models import Project, SummarySampleEventModel
from ..reports.fields import ReportField
from ..reports.formatters import (
    to_latitude,
    to_longitude,
    to_names,
    to_protocol_value,
    to_colonies_bleached,
    to_percent_cover,
    to_year,
    to_month,
    to_day,
)
from ..reports.report_serializer import ReportSerializer


class SummarySampleEventSerializer(BaseViewAPISerializer):
    id = None
    updated_by = None

    class Meta(BaseViewAPISerializer.Meta):
        model = SummarySampleEventModel
        exclude = BaseViewAPISerializer.Meta.exclude.copy()
        exclude.append("location")


class SummarySampleEventGeoSerializer(BaseViewAPIGeoSerializer):
    id = None
    updated_by = None

    class Meta(BaseViewAPIGeoSerializer.Meta):
        model = SummarySampleEventModel


class SummarySampleEventCSVSerializer(ReportSerializer):
    id = None

    fields = [
        ReportField("project_name", "Project name"),
        ReportField("country_name", "Country"),
        ReportField("site_name", "Site"),
        ReportField("location", "Latitude", to_latitude, alias="latitude"),
        ReportField("location", "Longitude", to_longitude, alias="longitude"),
        ReportField("reef_exposure", "Exposure"),
        ReportField("reef_type", "Reef type"),
        ReportField("reef_zone", "Reef zone"),
        ReportField("sample_date", "Year", to_year, "sample_date_year"),
        ReportField("sample_date", "Month", to_month, "sample_date_month"),
        ReportField("sample_date", "Day", to_day, "sample_date_day"),
        ReportField("management_name", "Management name"),
        ReportField("management_notes", "Management notes"),
        ReportField(
            "protocols",
            "Fish Belt transect count",
            to_protocol_value,
            protocol="beltfish",
            key="sample_unit_count",
        ),
        ReportField(
            "protocols",
            "Fish Belt average biomass (kg/ha)",
            to_protocol_value,
            protocol="beltfish",
            key="biomass_kgha_avg",
        ),
        ReportField(
            "protocols",
            "Fish Belt average biomass (kg/ha) by trophic group",
            to_protocol_value,
            protocol="beltfish",
            key="biomass_kgha_by_trophic_group_avg",
        ),
        ReportField(
            "protocols",
            "Benthic LIT transect count",
            to_protocol_value,
            protocol="benthiclit",
            key="sample_unit_count",
        ),
        ReportField(
            "protocols",
            "Benthic LIT average % cover by benthic category",
            to_protocol_value,
            protocol="benthiclit",
            key="percent_cover_by_benthic_category_avg",
        ),
        ReportField(
            "protocols",
            "Benthic PIT transect count",
            to_protocol_value,
            protocol="benthicpit",
            key="sample_unit_count",
        ),
        ReportField(
            "protocols",
            "Benthic PIT average % cover by benthic category",
            to_protocol_value,
            protocol="benthicpit",
            key="percent_cover_by_benthic_category_avg",
        ),
        ReportField(
            "protocols",
            "Habitat Complexity transect count",
            to_protocol_value,
            protocol="habitatcomplexity",
            key="sample_unit_count",
        ),
        ReportField(
            "protocols",
            "Habitat Complexity average score",
            to_protocol_value,
            protocol="habitatcomplexity",
            key="score_avg_avg",
        ),
        ReportField(
            "protocols",
            "Bleaching quadrat collection count",
            to_protocol_value,
            protocol="colonies_bleached",
            key="sample_unit_count",
        ),
        ReportField("protocols", "Bleaching colonies", to_colonies_bleached),
        ReportField("protocols", "Bleaching % cover", to_percent_cover),
        ReportField("contact_link", "Contact link"),
        ReportField("tags", "Organizations", to_names),
        ReportField("project_admins", "Project administrators", to_names),
        ReportField("data_policy_beltfish", "Fish Belt data sharing policy"),
        ReportField("data_policy_benthiclit", "Benthic LIT data sharing policy"),
        ReportField("data_policy_benthicpit", "Benthic PIT data sharing policy"),
        ReportField(
            "data_policy_habitatcomplexity", "Habitat Complexity data sharing policy"
        ),
        ReportField(
            "data_policy_bleachingqc",
            "Bleaching Quadrat Collection data sharing policy",
        ),
        ReportField("project_notes", "Project notes"),
        ReportField("site_notes", "Site notes"),
    ]

    additional_fields = [
        ReportField("project_id"),
        ReportField("sample_event_id"),
        ReportField("site_id"),
        ReportField("management_id"),
        ReportField("country_id"),
    ]


class SummarySampleEventFilterSet(AggregatedViewFilterSet):
    project_id = filters.BaseInFilter(method="id_lookup")
    project_name = filters.BaseInFilter(method="char_lookup")
    project_admins = filters.BaseInFilter(method="json_name_lookup")
    sample_date = filters.DateFromToRangeFilter()

    class Meta:
        model = SummarySampleEventModel
        fields = [
            "project_id",
            "project_name",
            "project_admins",
            "sample_date",
            "data_policy_beltfish",
            "data_policy_benthiclit",
            "data_policy_benthicpit",
            "data_policy_habitatcomplexity",
            "data_policy_bleachingqc",
        ]

        filter_overrides = {
            CharField: {
                "filter_class": filters.CharFilter,
                "extra": lambda f: {"lookup_expr": "icontains"},
            }
        }


class SummarySampleEventView(AggregatedViewMixin, BaseApiViewSet):
    drf_label = "summary-sample-event"
    permission_classes = [UnauthenticatedReadOnlyPermission]
    serializer_class = SummarySampleEventSerializer
    serializer_class_geojson = SummarySampleEventGeoSerializer
    serializer_class_csv = SummarySampleEventCSVSerializer
    filterset_class = SummarySampleEventFilterSet
    queryset = SummarySampleEventModel.objects.filter(~Q(project_status=Project.TEST))
    order_by = ("project_name", "site_name")
    # TODO: POST/create complex geometry filters? Too much of a pain to deal with pagination? Nobody currently uses...
    # TODO: documentation
