from django_filters import BaseInFilter, RangeFilter
from rest_condition import Or

from ...models import (
    BenthicPhotoQuadratTransectObsModel,
    BenthicPhotoQuadratTransectObsSQLModel,
    BenthicPhotoQuadratTransectSEModel,
    BenthicPhotoQuadratTransectSESQLModel,
    BenthicPhotoQuadratTransectSUModel,
    BenthicPhotoQuadratTransectSUSQLModel,
    BenthicPhotoQuadratTransect,
    ObsBenthicPhotoQuadrat,
)
from ...permissions import ProjectDataReadOnlyPermission, ProjectPublicSummaryPermission
from ...reports.fields import ReportField
from ...reports.formatters import (
    to_day,
    to_governance,
    to_month,
    to_names,
    to_str,
    to_year,
)
from ...reports.report_serializer import ReportSerializer
from ..base import (
    BaseProjectApiViewSet,
    BaseSEFilterSet,
    BaseSUObsFilterSet,
    BaseSUViewAPISerializer,
    BaseViewAPIGeoSerializer,
    BaseAPISerializer,
)
from ..observer import ObserverSerializer
from ..mixins import SampleUnitMethodEditMixin, SampleUnitMethodSummaryReport
from ..quadrat_transect import QuadratTransectSerializer
from ..sample_event import SampleEventSerializer
from . import BaseProjectMethodView


class BenthicPhotoQuadratTransectSerializer(BaseAPISerializer):
    class Meta:
        model = BenthicPhotoQuadratTransect
        exclude = []


class ObsBenthicPhotoQuadratSerializer(BaseAPISerializer):
    class Meta:
        model = ObsBenthicPhotoQuadrat
        exclude = []
        extra_kwargs = {
            "attribute": {
                "error_messages": {
                    "does_not_exist": 'Benthic attribute with id "{pk_value}", does not exist.'
                }
            }
        }


class BenthicPhotoQuadratTransectMethodSerializer(
    BenthicPhotoQuadratTransectSerializer
):
    sample_event = SampleEventSerializer(source="quadrat_transect.sample_event")
    quadrat_transect = QuadratTransectSerializer()
    observers = ObserverSerializer(many=True)
    obs_benthic_photo_quadrats = ObsBenthicPhotoQuadratSerializer(
        many=True, source="obsbenthicphotoquadrat_set"
    )

    class Meta:
        model = BenthicPhotoQuadratTransect
        exclude = []


class BenthicPhotoQuadratTransectMethodView(
    SampleUnitMethodSummaryReport, SampleUnitMethodEditMixin, BaseProjectApiViewSet
):
    queryset = BenthicPhotoQuadratTransect.objects.select_related(
        "quadrat_transect", "quadrat_transect__sample_event"
    ).order_by("updated_on", "id")
    serializer_class = BenthicPhotoQuadratTransectMethodSerializer
    http_method_names = ["get", "put", "head", "delete"]


class BenthicPQTMethodObsSerializer(BaseSUViewAPISerializer):
    class Meta(BaseSUViewAPISerializer.Meta):
        model = BenthicPhotoQuadratTransectObsModel
        exclude = BaseSUViewAPISerializer.Meta.exclude.copy()
        exclude.extend(["location", "observation_notes"])
        header_order = ["id"] + BaseSUViewAPISerializer.Meta.header_order.copy()
        header_order.extend(
            [
                "sample_unit_id",
                "sample_time",
                "transect_number",
                "label",
                "depth",
                "transect_len_surveyed",
                "reef_slope",
                "observers",
                "data_policy_benthicpqt",
                "interval_size",
                "interval_start",
                "interval",
                "benthic_category",
                "benthic_attribute",
                "growth_form",
                "percent_cover_by_benthic_category",
            ]
        )


class BenthicPQTMethodObsGeoSerializer(BaseViewAPIGeoSerializer):
    class Meta(BaseViewAPIGeoSerializer.Meta):
        model = BenthicPhotoQuadratTransectObsModel


class ObsBenthicPQTCSVSerializer(ReportSerializer):
    fields = [
        ReportField("project_name", "Project name"),
        ReportField("country_name", "Country"),
        ReportField("site_name", "Site"),
        ReportField("latitude", "Latitude"),
        ReportField("longitude", "Longitude"),
        ReportField("reef_exposure", "Exposure"),
        ReportField("reef_slope", "Reef slope"),
        ReportField("reef_type", "Reef type"),
        ReportField("reef_zone", "Reef zone"),
        ReportField("sample_date", "Year", to_year, "sample_date_year"),
        ReportField("sample_date", "Month", to_month, "sample_date_month"),
        ReportField("sample_date", "Day", to_day, "sample_date_day"),
        ReportField("sample_time", "Start time", to_str),
        ReportField("tide_name", "Tide"),
        ReportField("visibility_name", "Visibility"),
        ReportField("current_name", "Current"),
        ReportField("depth", "Depth"),
        ReportField("relative_depth", "Relative depth"),
        ReportField("management_name", "Management name"),
        ReportField("management_name_secondary", "Management secondary name"),
        ReportField("management_est_year", "Management year established"),
        ReportField("management_size", "Management size"),
        ReportField("management_parties", "Governance", to_governance),
        ReportField(
            "management_compliance",
            "Estimated compliance",
        ),
        ReportField("management_rules", "Management rules"),
        ReportField("transect_number", "Transect number"),
        ReportField("label", "Transect label"),
        ReportField("transect_len_surveyed", "Transect length surveyed"),
        ReportField("quadrat_size", "Quadrat size"),
        ReportField("num_quadrats", "Number of quadrats"),
        ReportField("num_points_per_quadrat", "Number of points per quadrat"),
        ReportField("observers", "Observers", to_names),
        ReportField("quadrat_number", "Quadrat Number"),
        ReportField("benthic_category", "Benthic category"),
        ReportField("benthic_attribute", "Benthic attribute"),
        ReportField("growth_form", "Growth form"),
        ReportField("num_points", "Number of points"),
        ReportField("site_notes", "Site notes"),
        ReportField("management_notes", "Management notes"),
        ReportField("sample_unit_notes", "Sample unit notes"),
    ]

    additional_fields = [
        ReportField("id"),
        ReportField("site_id"),
        ReportField("project_id"),
        ReportField("project_notes"),
        ReportField("contact_link"),
        ReportField("tags"),
        ReportField("country_id"),
        ReportField("management_id"),
        ReportField("sample_event_id"),
        ReportField("sample_unit_id"),
        ReportField("data_policy_benthicpqt"),
    ]


class BenthicPQTMethodSUSerializer(BaseSUViewAPISerializer):
    class Meta(BaseSUViewAPISerializer.Meta):
        model = BenthicPhotoQuadratTransectSUModel
        exclude = BaseSUViewAPISerializer.Meta.exclude.copy()
        exclude.append("location")
        header_order = BaseSUViewAPISerializer.Meta.header_order.copy()
        header_order.extend(
            [
                "label",
                "transect_number",
                "transect_len_surveyed",
                "depth",
                "reef_slope",
                "percent_cover_by_benthic_category",
                "data_policy_benthicpqt",
            ]
        )


class BenthicPQTMethodSUGeoSerializer(BaseViewAPIGeoSerializer):
    class Meta(BaseViewAPIGeoSerializer.Meta):
        model = BenthicPhotoQuadratTransectSUModel


class BenthicPQTMethodSUCSVSerializer(ReportSerializer):
    fields = [
        ReportField("project_name", "Project name"),
        ReportField("country_name", "Country"),
        ReportField("site_name", "Site"),
        ReportField("latitude", "Latitude"),
        ReportField("longitude", "Longitude"),
        ReportField("reef_exposure", "Exposure"),
        ReportField("reef_slope", "Reef slope"),
        ReportField("reef_type", "Reef type"),
        ReportField("reef_zone", "Reef zone"),
        ReportField("sample_date", "Year", to_year, "sample_date_year"),
        ReportField("sample_date", "Month", to_month, "sample_date_month"),
        ReportField("sample_date", "Day", to_day, "sample_date_day"),
        ReportField("sample_time", "Start time", to_str),
        ReportField("tide_name", "Tide"),
        ReportField("visibility_name", "Visibility"),
        ReportField("current_name", "Current"),
        ReportField("depth", "Depth"),
        ReportField("relative_depth", "Relative depth"),
        ReportField("management_name", "Management name"),
        ReportField("management_name_secondary", "Management secondary name"),
        ReportField("management_est_year", "Management year established"),
        ReportField("management_size", "Management size"),
        ReportField("management_parties", "Governance", to_governance),
        ReportField(
            "management_compliance",
            "Estimated compliance",
        ),
        ReportField("management_rules", "Management rules"),
        ReportField("transect_number", "Transect number"),
        ReportField("label", "Transect label"),
        ReportField("transect_len_surveyed", "Transect length surveyed"),
        ReportField("observers", "Observers", to_names),
        ReportField("num_points_nonother", "Number of non-Other points"),
        ReportField(
            "percent_cover_by_benthic_category", "Percent cover by benthic category"
        ),
        ReportField("site_notes", "Site notes"),
        ReportField("management_notes", "Management notes"),
        ReportField("sample_unit_notes", "Sample unit notes"),
    ]

    additional_fields = [
        ReportField("id"),
        ReportField("site_id"),
        ReportField("project_id"),
        ReportField("project_notes"),
        ReportField("contact_link"),
        ReportField("tags"),
        ReportField("country_id"),
        ReportField("management_id"),
        ReportField("sample_event_id"),
        ReportField("sample_unit_ids"),
        ReportField("data_policy_benthicpqt"),
    ]


class BenthicPQTMethodSESerializer(BaseSUViewAPISerializer):
    class Meta(BaseSUViewAPISerializer.Meta):
        model = BenthicPhotoQuadratTransectSEModel
        exclude = BaseSUViewAPISerializer.Meta.exclude.copy()
        exclude.append("location")
        header_order = BaseSUViewAPISerializer.Meta.header_order.copy()
        header_order.extend(
            [
                "data_policy_benthicpqt",
                "sample_unit_count",
                "depth_avg",
                "depth_sd",
                "percent_cover_by_benthic_category_avg",
                "percent_cover_by_benthic_category_sd",
            ]
        )


class BenthicPQTMethodSEGeoSerializer(BaseViewAPIGeoSerializer):
    class Meta(BaseViewAPIGeoSerializer.Meta):
        model = BenthicPhotoQuadratTransectSEModel


class BenthicPQTMethodSECSVSerializer(ReportSerializer):
    fields = [
        ReportField("project_name", "Project name"),
        ReportField("country_name", "Country"),
        ReportField("site_name", "Site"),
        ReportField("latitude", "Latitude"),
        ReportField("longitude", "Longitude"),
        ReportField("reef_exposure", "Exposure"),
        ReportField("reef_type", "Reef type"),
        ReportField("reef_zone", "Reef zone"),
        ReportField("sample_date", "Year", to_year, "sample_date_year"),
        ReportField("sample_date", "Month", to_month, "sample_date_month"),
        ReportField("sample_date", "Day", to_day, "sample_date_day"),
        ReportField("tide_name", "Tide"),
        ReportField("visibility_name", "Visibility"),
        ReportField("current_name", "Current"),
        ReportField("depth_avg", "Depth average"),
        ReportField("depth_sd", "Depth standard deviation"),
        ReportField("management_name", "Management name"),
        ReportField("management_name_secondary", "Management secondary name"),
        ReportField("management_est_year", "Management year established"),
        ReportField("management_size", "Management size"),
        ReportField("management_parties", "Governance", to_governance),
        ReportField(
            "management_compliance",
            "Estimated compliance",
        ),
        ReportField("management_rules", "Management rules"),
        ReportField("sample_unit_count", "Sample unit count"),
        ReportField("num_points_nonother", "Number of non-Other points"),
        ReportField(
            "percent_cover_by_benthic_category_avg",
            "Percent cover by benthic category average",
        ),
        ReportField(
            "percent_cover_by_benthic_category_sd",
            "Percent cover by benthic category standard deviation",
        ),
        ReportField("site_notes", "Site notes"),
        ReportField("management_notes", "Management notes"),
    ]

    additional_fields = [
        ReportField("id"),
        ReportField("site_id"),
        ReportField("project_id"),
        ReportField("project_notes"),
        ReportField("contact_link"),
        ReportField("tags"),
        ReportField("country_id"),
        ReportField("management_id"),
        ReportField("sample_event_id"),
        ReportField("data_policy_benthicpqt"),
    ]


class BenthicPQTMethodObsFilterSet(BaseSUObsFilterSet):
    transect_len_surveyed = RangeFilter()
    reef_slope = BaseInFilter(method="char_lookup")
    transect_number = BaseInFilter(method="char_lookup")
    benthic_category = BaseInFilter(method="char_lookup")
    benthic_attribute = BaseInFilter(method="char_lookup")
    growth_form = BaseInFilter(method="char_lookup")
    interval_size = RangeFilter()
    interval = RangeFilter()

    class Meta:
        model = BenthicPhotoQuadratTransectObsModel
        fields = [
            "transect_len_surveyed",
            "reef_slope",
            "transect_number",
            "num_quadrats",
            "num_points_per_quadrat",
            "quadrat_size",
            "quadrat_number",
            "benthic_category",
            "benthic_attribute",
            "growth_form",
        ]


class BenthicPQTMethodObsSQLFilterSet(BenthicPQTMethodObsFilterSet):
    class Meta(BenthicPQTMethodObsFilterSet.Meta):
        model = BenthicPhotoQuadratTransectObsSQLModel


class BenthicPQTMethodSUFilterSet(BaseSUObsFilterSet):
    transect_len_surveyed = RangeFilter()
    reef_slope = BaseInFilter(method="char_lookup")
    transect_number = BaseInFilter(method="char_lookup")

    class Meta:
        model = BenthicPhotoQuadratTransectSUModel
        fields = [
            "transect_len_surveyed",
            "reef_slope",
            "transect_number",
        ]


class BenthicPQTMethodSUSQLFilterSet(BenthicPQTMethodSUFilterSet):
    class Meta(BenthicPQTMethodSUFilterSet.Meta):
        model = BenthicPhotoQuadratTransectSUSQLModel


class BenthicPQTMethodSEFilterSet(BaseSEFilterSet):
    sample_unit_count = RangeFilter()
    depth_avg = RangeFilter()

    class Meta:
        model = BenthicPhotoQuadratTransectSEModel
        fields = [
            "sample_unit_count",
            "depth_avg",
        ]


class BenthicPQTMethodSESQLFilterSet(BenthicPQTMethodSEFilterSet):
    class Meta(BenthicPQTMethodSEFilterSet.Meta):
        model = BenthicPhotoQuadratTransectSESQLModel


class BenthicPQTProjectMethodObsView(BaseProjectMethodView):
    drf_label = "benthicphotoquadrattransect-obs"
    project_policy = "data_policy_benthicpqt"
    model = BenthicPhotoQuadratTransectObsModel
    serializer_class = BenthicPQTMethodObsSerializer
    serializer_class_geojson = BenthicPQTMethodObsGeoSerializer
    serializer_class_csv = ObsBenthicPQTCSVSerializer
    filterset_class = BenthicPQTMethodObsFilterSet
    order_by = (
        "site_name",
        "sample_date",
        "transect_number",
        "label",
        "quadrat_number",
    )


class BenthicPQTProjectMethodSUView(BaseProjectMethodView):
    drf_label = "benthicphotoquadrattransect-su"
    project_policy = "data_policy_benthicpqt"
    model = BenthicPhotoQuadratTransectSUModel
    serializer_class = BenthicPQTMethodSUSerializer
    serializer_class_geojson = BenthicPQTMethodSUGeoSerializer
    serializer_class_csv = BenthicPQTMethodSUCSVSerializer
    filterset_class = BenthicPQTMethodSUFilterSet
    order_by = ("site_name", "sample_date", "transect_number")


class BenthicPQTProjectMethodSEView(BaseProjectMethodView):
    drf_label = "benthicpqt-se"
    project_policy = "data_policy_benthicpqt"
    permission_classes = [
        Or(ProjectDataReadOnlyPermission, ProjectPublicSummaryPermission)
    ]
    model = BenthicPhotoQuadratTransectSEModel
    serializer_class = BenthicPQTMethodSESerializer
    serializer_class_geojson = BenthicPQTMethodSEGeoSerializer
    serializer_class_csv = BenthicPQTMethodSECSVSerializer
    filterset_class = BenthicPQTMethodSEFilterSet
    order_by = ("site_name", "sample_date")
