from django.db import transaction
from django_filters import BaseInFilter, RangeFilter
from rest_condition import Or
from rest_framework import status, serializers
from rest_framework.response import Response

from ...models import (
    HabitatComplexityObsModel,
    HabitatComplexityObsSQLModel,
    HabitatComplexitySEModel,
    HabitatComplexitySESQLModel,
    HabitatComplexitySUModel,
    HabitatComplexitySUSQLModel,
    HabitatComplexity,
    ObsHabitatComplexity,
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
    BaseViewAPIGeoSerializer,
    BaseSUViewAPISerializer,
    BaseAPISerializer,
)
from ..benthic_transect import BenthicTransectSerializer
from ..mixins import SampleUnitMethodSummaryReport, SampleUnitMethodEditMixin
from ..observer import ObserverSerializer
from ..sample_event import SampleEventSerializer
from . import (
    BaseProjectMethodView,
    clean_sample_event_models,
    save_model,
    save_one_to_many,
)


class HabitatComplexitySerializer(BaseAPISerializer):
    interval_size = serializers.DecimalField(
        max_digits=4,
        decimal_places=2,
        coerce_to_string=False,
        error_messages={"null": "Interval size is required"},
    )

    class Meta:
        model = HabitatComplexity
        exclude = []


class ObsHabitatComplexitySerializer(BaseAPISerializer):
    class Meta:
        model = ObsHabitatComplexity
        exclude = []


class HabitatComplexityMethodSerializer(HabitatComplexitySerializer):
    sample_event = SampleEventSerializer(source="transect.sample_event")
    benthic_transect = BenthicTransectSerializer(source="transect")
    observers = ObserverSerializer(many=True)
    obs_habitat_complexities = ObsHabitatComplexitySerializer(
        many=True, source="habitatcomplexity_set"
    )

    class Meta:
        model = HabitatComplexity
        exclude = []


class HabitatComplexityMethodView(SampleUnitMethodSummaryReport, SampleUnitMethodEditMixin, BaseProjectApiViewSet):
    queryset = (
        HabitatComplexity.objects.select_related("transect", "transect__sample_event")
        .all()
        .order_by("updated_on", "id")
    )
    serializer_class = HabitatComplexityMethodSerializer
    http_method_names = ["get", "put", "head", "delete"]

    @transaction.atomic
    def update(self, request, project_pk, pk=None):
        errors = {}
        is_valid = True
        nested_data = dict(
            sample_event=request.data.get("sample_event"),
            benthic_transect=request.data.get("benthic_transect"),
            observers=request.data.get("observers"),
            obs_habitat_complexities=request.data.get("obs_habitat_complexities"),
        )
        habitat_complexity_data = {
            k: v for k, v in request.data.items() if k not in nested_data
        }
        habitat_complexity_id = habitat_complexity_data["id"]

        context = dict(request=request)

        # Save models in a transaction
        sid = transaction.savepoint()
        try:
            habitat_complexity = HabitatComplexity.objects.get(id=habitat_complexity_id)

            # Observers
            check, errs = save_one_to_many(
                foreign_key=("transectmethod", habitat_complexity_id),
                database_records=habitat_complexity.observers.all(),
                data=request.data.get("observers") or [],
                serializer_class=ObserverSerializer,
                context=context,
            )
            if check is False:
                is_valid = False
                errors["observers"] = errs

            # Observations
            check, errs = save_one_to_many(
                foreign_key=("habitatcomplexity", habitat_complexity_id),
                database_records=habitat_complexity.habitatcomplexity_set.all(),
                data=request.data.get("obs_habitat_complexities") or [],
                serializer_class=ObsHabitatComplexitySerializer,
                context=context,
            )
            if check is False:
                is_valid = False
                errors["obs_habitat_complexities"] = errs

            # Sample Event
            check, errs = save_model(
                data=nested_data["sample_event"],
                serializer_class=SampleEventSerializer,
                context=context,
            )
            if check is False:
                is_valid = False
                errors["sample_event"] = errs

            # Benthic Transect
            check, errs = save_model(
                data=nested_data["benthic_transect"],
                serializer_class=BenthicTransectSerializer,
                context=context,
            )
            if check is False:
                is_valid = False
                errors["benthic_transect"] = errs

            # Habitat Complexity
            check, errs = save_model(
                data=habitat_complexity_data,
                serializer_class=HabitatComplexitySerializer,
                context=context,
            )
            if check is False:
                is_valid = False
                errors["habitat_complexity"] = errs

            if is_valid is False:
                transaction.savepoint_rollback(sid)
                return Response(data=errors, status=status.HTTP_400_BAD_REQUEST)

            clean_sample_event_models(nested_data["sample_event"])

            transaction.savepoint_commit(sid)

            habitat_complexity = HabitatComplexity.objects.get(id=habitat_complexity_id)
            return Response(
                HabitatComplexityMethodSerializer(habitat_complexity).data,
                status=status.HTTP_200_OK,
            )

        except:
            transaction.savepoint_rollback(sid)
            raise


class HabitatComplexityMethodObsSerializer(BaseSUViewAPISerializer):
    class Meta(BaseSUViewAPISerializer.Meta):
        model = HabitatComplexityObsModel
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
                "data_policy_habitatcomplexity",
                "interval",
                "score",
            ]
        )


class HabitatComplexityMethodObsGeoSerializer(BaseViewAPIGeoSerializer):
    class Meta(BaseViewAPIGeoSerializer.Meta):
        model = HabitatComplexityObsModel


class ObsHabitatComplexityCSVSerializer(ReportSerializer):
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
        ReportField("management_compliance", "Estimated compliance"),
        ReportField("management_rules", "Management rules"),
        ReportField("transect_number", "Transect number"),
        ReportField("label", "Transect label"),
        ReportField("transect_len_surveyed", "Transect length surveyed"),
        ReportField("observers", "Observers", to_names),
        ReportField("interval", "Interval (m)"),
        ReportField("score", "Habitat complexity value"),
        ReportField("score_name", "Habitat complexity name"),
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
        ReportField("interval_size"),
        ReportField("data_policy_habitatcomplexity"),
    ]


class HabitatComplexityMethodSUSerializer(BaseSUViewAPISerializer):
    class Meta(BaseSUViewAPISerializer.Meta):
        model = HabitatComplexitySUModel
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
                "score_avg",
                "data_policy_habitatcomplexity",
            ]
        )


class HabitatComplexityMethodSUGeoSerializer(BaseViewAPIGeoSerializer):
    class Meta(BaseViewAPIGeoSerializer.Meta):
        model = HabitatComplexitySUModel


class HabitatComplexityMethodSUCSVSerializer(ReportSerializer):
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
        ReportField("management_compliance", "Estimated compliance"),
        ReportField("management_rules", "Management rules"),
        ReportField("transect_number", "Transect number"),
        ReportField("label", "Transect label"),
        ReportField("transect_len_surveyed", "Transect length surveyed"),
        ReportField("observers", "Observers", to_names),
        ReportField("score_avg", "Score average"),
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
        ReportField("data_policy_habitatcomplexity"),
    ]


class HabitatComplexityMethodSESerializer(BaseSUViewAPISerializer):
    class Meta(BaseSUViewAPISerializer.Meta):
        model = HabitatComplexitySEModel
        exclude = BaseSUViewAPISerializer.Meta.exclude.copy()
        exclude.append("location")
        header_order = BaseSUViewAPISerializer.Meta.header_order.copy()
        header_order.extend(
            [
                "data_policy_habitatcomplexity",
                "sample_unit_count",
                "depth_avg",
                "depth_sd",
                "score_avg_avg",
            ]
        )


class HabitatComplexityMethodSEGeoSerializer(BaseViewAPIGeoSerializer):
    class Meta(BaseViewAPIGeoSerializer.Meta):
        model = HabitatComplexitySEModel


class HabitatComplexityMethodSECSVSerializer(ReportSerializer):
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
        ReportField("management_compliance", "Estimated compliance"),
        ReportField("management_rules", "Management rules"),
        ReportField("sample_unit_count", "Sample unit count"),
        ReportField("score_avg_avg", "Score average"),
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
        ReportField("data_policy_habitatcomplexity"),
    ]


class HabitatComplexityMethodObsFilterSet(BaseSUObsFilterSet):
    transect_len_surveyed = RangeFilter()
    reef_slope = BaseInFilter(method="char_lookup")
    transect_number = BaseInFilter(method="char_lookup")
    benthic_category = BaseInFilter(method="char_lookup")
    benthic_attribute = BaseInFilter(method="char_lookup")
    growth_form = BaseInFilter(method="char_lookup")
    interval = RangeFilter()
    score = RangeFilter()

    class Meta:
        model = HabitatComplexityObsModel
        fields = [
            "transect_len_surveyed",
            "reef_slope",
            "transect_number",
            "interval",
            "score",
        ]


class HabitatComplexityMethodObsSQLFilterSet(HabitatComplexityMethodObsFilterSet):
    class Meta(HabitatComplexityMethodObsFilterSet.Meta):
        model = HabitatComplexityObsSQLModel


class HabitatComplexityMethodSUFilterSet(BaseSUObsFilterSet):
    transect_len_surveyed = RangeFilter()
    reef_slope = BaseInFilter(method="char_lookup")
    transect_number = BaseInFilter(method="char_lookup")
    interval_size = RangeFilter()
    score_avg = RangeFilter()

    class Meta:
        model = HabitatComplexitySUModel
        fields = [
            "transect_len_surveyed",
            "reef_slope",
            "transect_number",
            "score_avg",
        ]


class HabitatComplexityMethodSUSQLFilterSet(HabitatComplexityMethodSUFilterSet):
    class Meta(HabitatComplexityMethodSUFilterSet.Meta):
        model = HabitatComplexitySUSQLModel


class HabitatComplexityMethodSEFilterSet(BaseSEFilterSet):
    sample_unit_count = RangeFilter()
    depth_avg = RangeFilter()
    score_avg_avg = RangeFilter()

    class Meta:
        model = HabitatComplexitySEModel
        fields = [
            "sample_unit_count",
            "depth_avg",
            "score_avg_avg",
        ]


class HabitatComplexityMethodSESQLFilterSet(HabitatComplexityMethodSEFilterSet):
    class Meta(HabitatComplexityMethodSEFilterSet.Meta):
        model = HabitatComplexitySESQLModel


class HabitatComplexityProjectMethodObsView(BaseProjectMethodView):
    drf_label = "habitatcomplexity-obs"
    project_policy = "data_policy_habitatcomplexity"
    model = HabitatComplexityObsModel
    serializer_class = HabitatComplexityMethodObsSerializer
    serializer_class_geojson = HabitatComplexityMethodObsGeoSerializer
    serializer_class_csv = ObsHabitatComplexityCSVSerializer
    filterset_class = HabitatComplexityMethodObsFilterSet
    order_by = ("site_name", "sample_date", "transect_number", "label", "interval")


class HabitatComplexityProjectMethodSUView(BaseProjectMethodView):
    drf_label = "habitatcomplexity-su"
    project_policy = "data_policy_habitatcomplexity"
    model = HabitatComplexitySUModel
    serializer_class = HabitatComplexityMethodSUSerializer
    serializer_class_geojson = HabitatComplexityMethodSUGeoSerializer
    serializer_class_csv = HabitatComplexityMethodSUCSVSerializer
    filterset_class = HabitatComplexityMethodSUFilterSet
    order_by = ("site_name", "sample_date", "transect_number")


class HabitatComplexityProjectMethodSEView(BaseProjectMethodView):
    drf_label = "habitatcomplexity-se"
    project_policy = "data_policy_habitatcomplexity"
    permission_classes = [
        Or(ProjectDataReadOnlyPermission, ProjectPublicSummaryPermission)
    ]
    model = HabitatComplexitySEModel
    serializer_class = HabitatComplexityMethodSESerializer
    serializer_class_geojson = HabitatComplexityMethodSEGeoSerializer
    serializer_class_csv = HabitatComplexityMethodSECSVSerializer
    filterset_class = HabitatComplexityMethodSEFilterSet
    order_by = ("site_name", "sample_date")
