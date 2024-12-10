from django.db.models import CharField, Q
from django_filters import rest_framework as filters
from rest_framework.serializers import SerializerMethodField

from ..models import Project, SummarySampleEventModel
from ..permissions import UnauthenticatedReadOnlyPermission
from ..reports.fields import ReportField
from ..reports.formatters import (
    to_colonies_bleached,
    to_day,
    to_governance,
    to_join_list,
    to_latitude,
    to_longitude,
    to_month,
    to_names,
    to_percent_cover,
    to_protocol_value,
    to_year,
)
from ..reports.report_serializer import ReportSerializer
from ..utils.project import get_citation_retrieved_text
from .base import AggregatedViewFilterSet, BaseViewAPIGeoSerializer, BaseViewAPISerializer
from .sampleunitmethods import AggregatedViewMixin, BaseApiViewSet


class SummarySampleEventSerializer(BaseViewAPISerializer):
    id = None
    updated_by = None
    suggested_citation = SerializerMethodField()

    def get_suggested_citation(self, obj):
        suggested_citation = ""
        if obj.suggested_citation != "":
            suggested_citation = f"{obj.suggested_citation} "
        return f"{suggested_citation}{get_citation_retrieved_text(obj.project_name)}"

    class Meta(BaseViewAPISerializer.Meta):
        model = SummarySampleEventModel
        exclude = BaseViewAPISerializer.Meta.exclude.copy()
        exclude.extend(["id", "location"])


class SummarySampleEventGeoSerializer(BaseViewAPIGeoSerializer):
    id = None
    updated_by = None

    class Meta(BaseViewAPIGeoSerializer.Meta):
        model = SummarySampleEventModel
        exclude = ["id"]


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
        ReportField("management_est_year", "Management year established"),
        ReportField("management_size", "Management size"),
        ReportField("management_parties", "Governance", to_governance),
        ReportField("management_compliance", "Estimated compliance"),
        ReportField("management_rules", "Management rules", to_join_list),
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
            "Fish Belt biomass (kg/ha) standard deviation",
            to_protocol_value,
            protocol="beltfish",
            key="biomass_kgha_sd",
        ),
        ReportField(
            "protocols",
            "Fish Belt average biomass (kg/ha) by trophic group",
            to_protocol_value,
            protocol="beltfish",
            key="biomass_kgha_trophic_group_avg",
        ),
        ReportField(
            "protocols",
            "Fish Belt biomass (kg/ha) standard deviation by trophic group",
            to_protocol_value,
            protocol="beltfish",
            key="biomass_kgha_trophic_group_sd",
        ),
        ReportField(
            "protocols",
            "Fish Belt average biomass (kg/ha) by family",
            to_protocol_value,
            protocol="beltfish",
            key="biomass_kgha_fish_family_avg",
        ),
        ReportField(
            "protocols",
            "Fish Belt biomass (kg/ha) standard deviation by family",
            to_protocol_value,
            protocol="beltfish",
            key="biomass_kgha_fish_family_sd",
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
            "Benthic LIT % cover average by benthic category",
            to_protocol_value,
            protocol="benthiclit",
            key="percent_cover_benthic_category_avg",
        ),
        ReportField(
            "protocols",
            "Benthic LIT % cover standard deviation by benthic category",
            to_protocol_value,
            protocol="benthiclit",
            key="percent_cover_benthic_category_sd",
        ),
        ReportField(
            "protocols",
            "Benthic LIT % cover average by life history",
            to_protocol_value,
            protocol="benthiclit",
            key="percent_cover_life_histories_avg",
        ),
        ReportField(
            "protocols",
            "Benthic LIT % cover standard deviation by life history",
            to_protocol_value,
            protocol="benthiclit",
            key="percent_cover_life_histories_sd",
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
            "Benthic PIT % cover average by benthic category",
            to_protocol_value,
            protocol="benthicpit",
            key="percent_cover_benthic_category_avg",
        ),
        ReportField(
            "protocols",
            "Benthic PIT % cover standard deviation by benthic category",
            to_protocol_value,
            protocol="benthicpit",
            key="percent_cover_benthic_category_sd",
        ),
        ReportField(
            "protocols",
            "Benthic PIT % cover average by life history",
            to_protocol_value,
            protocol="benthicpit",
            key="percent_cover_life_histories_avg",
        ),
        ReportField(
            "protocols",
            "Benthic PIT % cover standard deviation by life history",
            to_protocol_value,
            protocol="benthicpit",
            key="percent_cover_life_histories_sd",
        ),
        ReportField(
            "protocols",
            "Benthic PQT transect count",
            to_protocol_value,
            protocol="benthicpqt",
            key="sample_unit_count",
        ),
        ReportField(
            "protocols",
            "Benthic PQT % cover average by benthic category",
            to_protocol_value,
            protocol="benthicpqt",
            key="percent_cover_benthic_category_avg",
        ),
        ReportField(
            "protocols",
            "Benthic PQT % cover standard deviation by benthic category",
            to_protocol_value,
            protocol="benthicpqt",
            key="percent_cover_benthic_category_sd",
        ),
        ReportField(
            "protocols",
            "Benthic PQT % cover average by life history",
            to_protocol_value,
            protocol="benthicpqt",
            key="percent_cover_life_histories_avg",
        ),
        ReportField(
            "protocols",
            "Benthic PQT % cover standard deviation by life history",
            to_protocol_value,
            protocol="benthicpqt",
            key="percent_cover_life_histories_sd",
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
            "Habitat Complexity score standard deviation",
            to_protocol_value,
            protocol="habitatcomplexity",
            key="score_avg_sd",
        ),
        ReportField(
            "protocols",
            "Habitat Complexity observations count average",
            to_protocol_value,
            protocol="habitatcomplexity",
            key="observation_count_avg",
        ),
        ReportField(
            "protocols",
            "Habitat Complexity observations count standard deviation",
            to_protocol_value,
            protocol="habitatcomplexity",
            key="observation_count_sd",
        ),
        ReportField(
            "protocols",
            "Bleaching quadrat collection count",
            to_protocol_value,
            protocol="colonies_bleached",
            key="sample_unit_count",
        ),
        ReportField(
            "protocols",
            "Bleaching colonies",
            to_colonies_bleached,
            protocol="colonies_bleached",
            key="percent_bleached",
        ),
        ReportField(
            "protocols",
            "Bleaching % cover",
            to_percent_cover,
            protocol="quadrat_benthic_percent",
            key="percent_cover",
        ),
        ReportField(
            "protocols",
            "Bleaching % cover average by life history",
            to_protocol_value,
            protocol="colonies_bleached",
            key="percent_cover_life_histories_avg",
        ),
        ReportField(
            "protocols",
            "Bleaching % cover standard deviation by life history",
            to_protocol_value,
            protocol="colonies_bleached",
            key="percent_cover_life_histories_sd",
        ),
        ReportField("contact_link", "Contact link"),
        ReportField("tags", "Organizations", to_names),
        ReportField("project_admins", "Project administrators", to_names),
        ReportField("data_policy_beltfish", "Fish Belt data sharing policy"),
        ReportField("data_policy_benthiclit", "Benthic LIT data sharing policy"),
        ReportField("data_policy_benthicpit", "Benthic PIT data sharing policy"),
        ReportField("data_policy_habitatcomplexity", "Habitat Complexity data sharing policy"),
        ReportField(
            "data_policy_bleachingqc",
            "Bleaching Quadrat Collection data sharing policy",
        ),
        ReportField(
            "data_policy_benthicpqt",
            "Photo Quadrat Transect data sharing policy",
        ),
        ReportField("project_notes", "Project notes"),
        ReportField("suggested_citation", "Suggested citation"),
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
            "data_policy_benthicpqt",
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
