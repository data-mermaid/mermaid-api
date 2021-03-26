from django.db.models import Q, CharField
from django_filters import rest_framework as filters
from .base import (
    BaseViewAPIGeoSerializer,
    BaseViewAPISerializer,
    AggregatedViewFilterSet,
)
from .sample_units import AggregatedViewMixin, BaseApiViewSet
from ..permissions import UnauthenticatedReadOnlyPermission
from api.models.view_models.summary_site import SummarySiteViewModel
from ..models import Project
from ..reports.fields import ReportField
from ..reports.formatters import (
    to_latitude,
    to_longitude,
    to_names,
    to_protocol_value,
    to_colonies_bleached,
    to_percent_cover,
)
from ..reports.report_serializer import ReportSerializer


class SummarySiteSerializer(BaseViewAPISerializer):
    id = None
    updated_by = None

    class Meta(BaseViewAPISerializer.Meta):
        model = SummarySiteViewModel
        exclude = BaseViewAPISerializer.Meta.exclude.copy()
        exclude.append("location")


class SummarySiteGeoSerializer(BaseViewAPIGeoSerializer):
    id = None
    updated_by = None

    class Meta(BaseViewAPIGeoSerializer.Meta):
        model = SummarySiteViewModel


class SummarySiteCSVSerializer(ReportSerializer):
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
        ReportField("date_min", "Earliest date"),
        ReportField("date_max", "Most recent date"),
        ReportField("depth_avg_min", "Minimum average depth"),
        ReportField("depth_avg_max", "Maximum average depth"),
        ReportField("management_regimes", "Management regimes", to_names),
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
        ReportField("site_id"),
        ReportField("country_id"),
    ]


class SummarySiteFilterSet(AggregatedViewFilterSet):
    project_id = filters.BaseInFilter(method="id_lookup")
    project_name = filters.BaseInFilter(method="char_lookup")
    project_admins = filters.BaseInFilter(method="json_name_lookup")
    date_min = filters.DateFromToRangeFilter()
    date_max = filters.DateFromToRangeFilter()

    class Meta:
        model = SummarySiteViewModel
        fields = [
            "project_id",
            "project_name",
            "project_admins",
            "date_min",
            "date_max",
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


# max_page_size now = 1000 not 5000
class SummarySiteView(AggregatedViewMixin, BaseApiViewSet):
    drf_label = "summary-site"
    permission_classes = [UnauthenticatedReadOnlyPermission]
    serializer_class = SummarySiteSerializer
    serializer_class_geojson = SummarySiteGeoSerializer
    serializer_class_csv = SummarySiteCSVSerializer
    filterset_class = SummarySiteFilterSet
    queryset = SummarySiteViewModel.objects.filter(
        ~Q(project_status=Project.TEST)  # replace with solution for filtering generally
        & Q(management_regimes__isnull=False)
    )
    order_by = ("project_name", "site_name")
    # TODO: POST/create complex geometry filters? Too much of a pain to deal with pagination? Nobody currently uses...
    # TODO: documentation
