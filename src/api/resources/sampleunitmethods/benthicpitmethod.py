from django.db import transaction
from django_filters import BaseInFilter, RangeFilter
from rest_condition import Or
from rest_framework import serializers, status
from rest_framework.response import Response

from ...models import (
    BenthicPIT,
    BenthicPITObsModel,
    BenthicPITObsSQLModel,
    BenthicPITSEModel,
    BenthicPITSESQLModel,
    BenthicPITSUModel,
    BenthicPITSUSQLModel,
    ObsBenthicPIT,
)
from ...permissions import ProjectDataReadOnlyPermission, ProjectPublicSummaryPermission
from ...reports.fields import ReportField
from ...reports.formatters import (
    to_day,
    to_governance,
    to_join_list,
    to_life_history,
    to_month,
    to_names,
    to_str,
    to_year,
)
from ...reports.report_serializer import ReportSerializer
from ..base import (
    BaseAPISerializer,
    BaseProjectApiViewSet,
    BaseSEFilterSet,
    BaseSUObsFilterSet,
    BaseSUViewAPISerializer,
    BaseSUViewAPISUSerializer,
    BaseViewAPIGeoSerializer,
    BaseViewAPISUGeoSerializer,
)
from ..benthic_transect import BenthicTransectSerializer
from ..mixins import SampleUnitMethodEditMixin, SampleUnitMethodSummaryReport
from ..observer import ObserverSerializer
from ..sample_event import SampleEventSerializer
from . import (
    BaseProjectMethodView,
    clean_sample_event_models,
    save_model,
    save_one_to_many,
)


class BenthicPITSerializer(BaseAPISerializer):
    interval_size = serializers.DecimalField(
        max_digits=4,
        decimal_places=2,
        coerce_to_string=False,
        error_messages={"null": "Interval size is required"},
    )

    interval_start = serializers.DecimalField(
        max_digits=4,
        decimal_places=2,
        coerce_to_string=False,
        error_messages={"null": "Interval start is required"},
    )

    class Meta:
        model = BenthicPIT
        exclude = []


class ObsBenthicPITSerializer(BaseAPISerializer):
    class Meta:
        model = ObsBenthicPIT
        exclude = []
        extra_kwargs = {
            "attribute": {
                "error_messages": {
                    "does_not_exist": 'Benthic attribute with id "{pk_value}", does not exist.'
                }
            }
        }


class BenthicPITMethodSerializer(BenthicPITSerializer):
    sample_event = SampleEventSerializer(source="transect.sample_event")
    benthic_transect = BenthicTransectSerializer(source="transect")
    observers = ObserverSerializer(many=True)
    obs_benthic_pits = ObsBenthicPITSerializer(many=True, source="obsbenthicpit_set")

    class Meta:
        model = BenthicPIT
        exclude = []


class BenthicPITMethodView(
    SampleUnitMethodSummaryReport, SampleUnitMethodEditMixin, BaseProjectApiViewSet
):
    queryset = (
        BenthicPIT.objects.select_related("transect", "transect__sample_event")
        .all()
        .order_by("updated_on", "id")
    )
    serializer_class = BenthicPITMethodSerializer
    http_method_names = ["get", "put", "head", "delete"]

    @transaction.atomic
    def update(self, request, project_pk, pk=None):
        errors = {}
        is_valid = True
        nested_data = dict(
            sample_event=request.data.get("sample_event"),
            benthic_transect=request.data.get("benthic_transect"),
            observers=request.data.get("observers"),
            obs_benthic_pits=request.data.get("obs_benthic_pits"),
        )
        benthic_pit_data = {k: v for k, v in request.data.items() if k not in nested_data}
        benthic_pit_id = benthic_pit_data["id"]

        context = dict(request=request)

        # Save models in a transaction
        sid = transaction.savepoint()
        try:
            benthic_pit = BenthicPIT.objects.get(id=benthic_pit_id)

            # Observers
            check, errs = save_one_to_many(
                foreign_key=("transectmethod", benthic_pit_id),
                database_records=benthic_pit.observers.all(),
                data=request.data.get("observers") or [],
                serializer_class=ObserverSerializer,
                context=context,
            )
            if check is False:
                is_valid = False
                errors["observers"] = errs

            # Observations
            check, errs = save_one_to_many(
                foreign_key=("benthicpit", benthic_pit_id),
                database_records=benthic_pit.obsbenthicpit_set.all(),
                data=request.data.get("obs_benthic_pits") or [],
                serializer_class=ObsBenthicPITSerializer,
                context=context,
            )
            if check is False:
                is_valid = False
                errors["obs_benthic_pits"] = errs

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

            # Benthic PIT
            check, errs = save_model(
                data=benthic_pit_data,
                serializer_class=BenthicPITSerializer,
                context=context,
            )
            if check is False:
                is_valid = False
                errors["benthic_pit"] = errs

            if is_valid is False:
                transaction.savepoint_rollback(sid)
                return Response(data=errors, status=status.HTTP_400_BAD_REQUEST)

            clean_sample_event_models(nested_data["sample_event"])

            transaction.savepoint_commit(sid)

            benthic_pit = BenthicPIT.objects.get(id=benthic_pit_id)
            return Response(BenthicPITMethodSerializer(benthic_pit).data, status=status.HTTP_200_OK)

        except:
            transaction.savepoint_rollback(sid)
            raise


class BenthicPITMethodObsSerializer(BaseSUViewAPISerializer):
    class Meta(BaseSUViewAPISerializer.Meta):
        model = BenthicPITObsModel
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
                "data_policy_benthicpit",
                "interval_size",
                "interval_start",
                "interval",
                "benthic_category",
                "benthic_attribute",
                "growth_form",
                "life_histories",
                "percent_cover_benthic_category",
            ]
        )


class BenthicPITMethodObsGeoSerializer(BaseViewAPIGeoSerializer):
    class Meta(BaseViewAPIGeoSerializer.Meta):
        model = BenthicPITObsModel


class ObsBenthicPITCSVSerializer(ReportSerializer):
    fields = [
        ReportField("project_name", "Project name"),
        ReportField("project_admins", "Project admins", to_names),
        ReportField("country_name", "Country"),
        ReportField("contact_link", "Project contact link"),
        ReportField("tags", "Project organizations", to_names),
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
        ReportField("management_rules", "Management rules", to_join_list),
        ReportField("transect_number", "Transect number"),
        ReportField("label", "Transect label"),
        ReportField("transect_len_surveyed", "Transect length surveyed"),
        ReportField("observers", "Observers", to_names),
        ReportField("interval", "PIT interval (m)"),
        ReportField("benthic_category", "Benthic category"),
        ReportField("benthic_attribute", "Benthic attribute"),
        ReportField("growth_form", "Growth form"),
        ReportField(
            "life_histories",
            "Competitive",
            to_life_history,
            protocol="life_histories",
            key="competitive",
        ),
        ReportField(
            "life_histories",
            "Generalist",
            to_life_history,
            protocol="life_histories",
            key="generalist",
        ),
        ReportField(
            "life_histories",
            "Stress-tolerant",
            to_life_history,
            protocol="life_histories",
            key="stress-tolerant",
        ),
        ReportField(
            "life_histories", "Weedy", to_life_history, protocol="life_histories", key="weedy"
        ),
        ReportField("site_notes", "Site notes"),
        ReportField("management_notes", "Management notes"),
        ReportField("sample_unit_notes", "Sample unit notes"),
        ReportField("project_notes", "Project notes"),
        ReportField("data_policy_benthicpit", "Benthic PIT data policy"),
        ReportField("site_id"),
    ]

    additional_fields = [
        ReportField("id"),
        ReportField("project_id"),
        ReportField("country_id"),
        ReportField("management_id"),
        ReportField("sample_event_id"),
        ReportField("sample_unit_id"),
        ReportField("interval_size"),
        ReportField("interval_start"),
    ]


class BenthicPITMethodSUSerializer(BaseSUViewAPISUSerializer):
    class Meta(BaseSUViewAPISUSerializer.Meta):
        model = BenthicPITSUModel
        exclude = BaseSUViewAPISUSerializer.Meta.exclude.copy()
        exclude.append("location")
        header_order = BaseSUViewAPISUSerializer.Meta.header_order.copy()
        header_order.extend(
            [
                "label",
                "transect_number",
                "transect_len_surveyed",
                "depth",
                "reef_slope",
                "interval_size",
                "interval_start",
                "percent_cover_benthic_category",
                "percent_cover_life_histories",
                "data_policy_benthicpit",
            ]
        )


class BenthicPITMethodSUGeoSerializer(BaseViewAPISUGeoSerializer):
    class Meta(BaseViewAPISUGeoSerializer.Meta):
        model = BenthicPITSUModel


class BenthicPITMethodSUCSVSerializer(ReportSerializer):
    fields = [
        ReportField("project_name", "Project name"),
        ReportField("project_admins", "Project admins", to_names),
        ReportField("country_name", "Country"),
        ReportField("contact_link", "Project contact link"),
        ReportField("tags", "Project organizations", to_names),
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
        ReportField("management_rules", "Management rules", to_join_list),
        ReportField("transect_number", "Transect number"),
        ReportField("label", "Transect label"),
        ReportField("transect_len_surveyed", "Transect length surveyed"),
        ReportField("observers", "Observers", to_names),
        ReportField("interval_size", "Interval size"),
        ReportField("interval_start", "Interval start"),
        ReportField("percent_cover_benthic_category", "Percent cover by benthic category"),
        ReportField("percent_cover_life_histories", "Percent cover by life history"),
        ReportField("site_notes", "Site notes"),
        ReportField("management_notes", "Management notes"),
        ReportField("sample_unit_notes", "Sample unit notes"),
        ReportField("project_notes", "Project notes"),
        ReportField("data_policy_benthicpit", "Benthic PIT data policy"),
        ReportField("site_id"),
    ]

    additional_fields = [
        ReportField("project_id"),
        ReportField("country_id"),
        ReportField("management_id"),
        ReportField("sample_event_id"),
        ReportField("sample_unit_ids"),
    ]


class BenthicPITMethodSESerializer(BaseSUViewAPISerializer):
    class Meta(BaseSUViewAPISerializer.Meta):
        model = BenthicPITSEModel
        exclude = BaseSUViewAPISerializer.Meta.exclude.copy()
        exclude.append("location")
        header_order = BaseSUViewAPISerializer.Meta.header_order.copy()
        header_order.extend(
            [
                "data_policy_benthicpit",
                "sample_unit_count",
                "depth_avg",
                "depth_sd",
                "percent_cover_benthic_category_avg",
                "percent_cover_benthic_category_sd",
                "percent_cover_life_histories_avg",
                "percent_cover_life_histories_sd",
            ]
        )


class BenthicPITMethodSEGeoSerializer(BaseViewAPIGeoSerializer):
    class Meta(BaseViewAPIGeoSerializer.Meta):
        model = BenthicPITSEModel


class BenthicPITMethodSECSVSerializer(ReportSerializer):
    fields = [
        ReportField("project_name", "Project name"),
        ReportField("project_admins", "Project admins", to_names),
        ReportField("country_name", "Country"),
        ReportField("contact_link", "Project contact link"),
        ReportField("tags", "Project organizations", to_names),
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
        ReportField("management_rules", "Management rules", to_join_list),
        ReportField("sample_unit_count", "Sample unit count"),
        ReportField(
            "percent_cover_benthic_category_avg",
            "Percent cover by benthic category average",
        ),
        ReportField(
            "percent_cover_benthic_category_sd",
            "Percent cover by benthic category standard deviation",
        ),
        ReportField("percent_cover_life_histories_avg", "Percent cover by life history average"),
        ReportField(
            "percent_cover_life_histories_sd", "Percent cover by life history standard deviation"
        ),
        ReportField("site_notes", "Site notes"),
        ReportField("management_notes", "Management notes"),
        ReportField("project_notes", "Project notes"),
        ReportField("data_policy_benthicpit", "Benthic PIT data policy"),
        ReportField("site_id"),
    ]

    additional_fields = [
        ReportField("id"),
        ReportField("project_id"),
        ReportField("country_id"),
        ReportField("management_id"),
        ReportField("sample_event_id"),
    ]


class BenthicPITMethodObsFilterSet(BaseSUObsFilterSet):
    transect_len_surveyed = RangeFilter()
    reef_slope = BaseInFilter(method="char_lookup")
    transect_number = BaseInFilter(method="char_lookup")
    benthic_category = BaseInFilter(method="char_lookup")
    benthic_attribute = BaseInFilter(method="char_lookup")
    growth_form = BaseInFilter(method="char_lookup")
    interval_size = RangeFilter()
    interval = RangeFilter()

    class Meta:
        model = BenthicPITObsModel
        fields = [
            "transect_len_surveyed",
            "reef_slope",
            "transect_number",
            "interval_size",
            "interval",
            "benthic_category",
            "benthic_attribute",
            "growth_form",
        ]


class BenthicPITMethodObsSQLFilterSet(BenthicPITMethodObsFilterSet):
    class Meta(BenthicPITMethodObsFilterSet.Meta):
        model = BenthicPITObsSQLModel


class BenthicPITMethodSUFilterSet(BaseSUObsFilterSet):
    transect_len_surveyed = RangeFilter()
    reef_slope = BaseInFilter(method="char_lookup")
    transect_number = BaseInFilter(method="char_lookup")
    interval_size = RangeFilter()

    class Meta:
        model = BenthicPITSUModel
        fields = [
            "transect_len_surveyed",
            "reef_slope",
            "transect_number",
            "interval_size",
        ]


class BenthicPITMethodSUSQLFilterSet(BenthicPITMethodSUFilterSet):
    class Meta(BenthicPITMethodSUFilterSet.Meta):
        model = BenthicPITSUSQLModel


class BenthicPITMethodSEFilterSet(BaseSEFilterSet):
    sample_unit_count = RangeFilter()
    depth_avg = RangeFilter()

    class Meta:
        model = BenthicPITSEModel
        fields = ["sample_unit_count", "depth_avg"]


class BenthicPITMethodSESQLFilterSet(BenthicPITMethodSEFilterSet):
    class Meta(BenthicPITMethodSEFilterSet.Meta):
        model = BenthicPITSESQLModel


class BenthicPITProjectMethodObsView(BaseProjectMethodView):
    drf_label = "benthicpit-obs"
    project_policy = "data_policy_benthicpit"
    model = BenthicPITObsModel
    serializer_class = BenthicPITMethodObsSerializer
    serializer_class_geojson = BenthicPITMethodObsGeoSerializer
    serializer_class_csv = ObsBenthicPITCSVSerializer
    filterset_class = BenthicPITMethodObsFilterSet
    order_by = ("site_name", "sample_date", "transect_number", "label", "interval")


class BenthicPITProjectMethodSUView(BaseProjectMethodView):
    drf_label = "benthicpit-su"
    project_policy = "data_policy_benthicpit"
    model = BenthicPITSUModel
    serializer_class = BenthicPITMethodSUSerializer
    serializer_class_geojson = BenthicPITMethodSUGeoSerializer
    serializer_class_csv = BenthicPITMethodSUCSVSerializer
    filterset_class = BenthicPITMethodSUFilterSet
    order_by = ("site_name", "sample_date", "transect_number")


class BenthicPITProjectMethodSEView(BaseProjectMethodView):
    drf_label = "benthicpit-se"
    project_policy = "data_policy_benthicpit"
    permission_classes = [Or(ProjectDataReadOnlyPermission, ProjectPublicSummaryPermission)]
    model = BenthicPITSEModel
    serializer_class = BenthicPITMethodSESerializer
    serializer_class_geojson = BenthicPITMethodSEGeoSerializer
    serializer_class_csv = BenthicPITMethodSECSVSerializer
    filterset_class = BenthicPITMethodSEFilterSet
    order_by = ("site_name", "sample_date")
