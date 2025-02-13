from django.db import transaction
from django_filters import BaseInFilter, RangeFilter
from rest_condition import Or
from rest_framework import status
from rest_framework.response import Response

from ...models import (
    BenthicLIT,
    BenthicLITObsModel,
    BenthicLITObsSQLModel,
    BenthicLITSEModel,
    BenthicLITSESQLModel,
    BenthicLITSUModel,
    BenthicLITSUSQLModel,
    ObsBenthicLIT,
)
from ...permissions import ProjectDataReadOnlyPermission, ProjectPublicSummaryPermission
from ...reports.fields import ReportField
from ...reports.formatters import (
    to_day,
    to_governance,
    to_join_list,
    to_latitude,
    to_life_history,
    to_longitude,
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


class BenthicLITSerializer(BaseAPISerializer):
    class Meta:
        model = BenthicLIT
        exclude = []


class ObsBenthicLITSerializer(BaseAPISerializer):
    class Meta:
        model = ObsBenthicLIT
        exclude = []
        extra_kwargs = {
            "attribute": {
                "error_messages": {
                    "does_not_exist": 'Benthic attribute with id "{pk_value}", does not exist.'
                }
            }
        }


class BenthicLITMethodSerializer(BenthicLITSerializer):
    sample_event = SampleEventSerializer(source="transect.sample_event")
    benthic_transect = BenthicTransectSerializer(source="transect")
    observers = ObserverSerializer(many=True)
    obs_benthic_lits = ObsBenthicLITSerializer(many=True, source="obsbenthiclit_set")

    class Meta:
        model = BenthicLIT
        exclude = []


class BenthicLITMethodView(
    SampleUnitMethodSummaryReport, SampleUnitMethodEditMixin, BaseProjectApiViewSet
):
    queryset = (
        BenthicLIT.objects.select_related("transect", "transect__sample_event")
        .all()
        .order_by("updated_on", "id")
    )
    serializer_class = BenthicLITMethodSerializer
    http_method_names = ["get", "put", "head", "delete"]

    @transaction.atomic
    def update(self, request, project_pk, pk=None):
        errors = {}
        is_valid = True
        nested_data = dict(
            sample_event=request.data.get("sample_event"),
            benthic_transect=request.data.get("benthic_transect"),
            observers=request.data.get("observers"),
            obs_benthic_lits=request.data.get("obs_benthic_lits"),
        )
        benthic_lit_data = {k: v for k, v in request.data.items() if k not in nested_data}
        benthic_lit_id = benthic_lit_data["id"]

        context = dict(request=request)

        # Save models in a transaction
        sid = transaction.savepoint()
        try:
            benthic_lit = BenthicLIT.objects.get(id=benthic_lit_id)

            # Observers
            check, errs = save_one_to_many(
                foreign_key=("transectmethod", benthic_lit_id),
                database_records=benthic_lit.observers.all(),
                data=request.data.get("observers") or [],
                serializer_class=ObserverSerializer,
                context=context,
            )
            if check is False:
                is_valid = False
                errors["observers"] = errs

            # Observations
            check, errs = save_one_to_many(
                foreign_key=("benthiclit", benthic_lit_id),
                database_records=benthic_lit.obsbenthiclit_set.all(),
                data=request.data.get("obs_benthic_lits") or [],
                serializer_class=ObsBenthicLITSerializer,
                context=context,
            )
            if check is False:
                is_valid = False
                errors["obs_benthic_lits"] = errs

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

            # Benthic LIT
            check, errs = save_model(
                data=benthic_lit_data,
                serializer_class=BenthicLITSerializer,
                context=context,
            )
            if check is False:
                is_valid = False
                errors["benthic_lit"] = errs

            if is_valid is False:
                transaction.savepoint_rollback(sid)
                return Response(data=errors, status=status.HTTP_400_BAD_REQUEST)

            clean_sample_event_models(nested_data["sample_event"])

            transaction.savepoint_commit(sid)

            benthic_lit = BenthicLIT.objects.get(id=benthic_lit_id)
            return Response(BenthicLITMethodSerializer(benthic_lit).data, status=status.HTTP_200_OK)

        except:
            transaction.savepoint_rollback(sid)
            raise


class BenthicLITMethodObsSerializer(BaseSUViewAPISerializer):
    class Meta(BaseSUViewAPISerializer.Meta):
        model = BenthicLITObsModel
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
                "data_policy_benthiclit",
                "length",
                "benthic_category",
                "benthic_attribute",
                "growth_form",
                "life_histories",
            ]
        )


class BenthicLITMethodObsGeoSerializer(BaseViewAPIGeoSerializer):
    class Meta(BaseViewAPIGeoSerializer.Meta):
        model = BenthicLITObsModel


class ObsBenthicLITCSVSerializer(ReportSerializer):
    fields = [
        ReportField("project_name", "Project name"),
        ReportField("project_admins", "Project admins", to_names),
        ReportField("country_name", "Country"),
        ReportField("contact_link", "Project contact link"),
        ReportField("tags", "Project organizations", to_names),
        ReportField("site_name", "Site"),
        ReportField("location", "Latitude", to_latitude, alias="latitude"),
        ReportField("location", "Longitude", to_longitude, alias="longitude"),
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
        ReportField("benthic_category", "Benthic category"),
        ReportField("benthic_attribute", "Benthic attribute"),
        ReportField("growth_form", "Growth form"),
        ReportField("length", "LIT (cm)"),
        ReportField("total_length", "Total transect cm"),
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
        ReportField("project_includes_gfcr", "Project includes GFCR"),
        ReportField("suggested_citation", "Suggested citation"),
        ReportField("data_policy_benthiclit", "Benthic LIT data policy"),
        ReportField("site_id"),
    ]

    additional_fields = [
        ReportField("id"),
        ReportField("project_id"),
        ReportField("country_id"),
        ReportField("management_id"),
        ReportField("sample_event_id"),
        ReportField("sample_unit_id"),
    ]


class BenthicLITMethodSUSerializer(BaseSUViewAPISUSerializer):
    class Meta(BaseSUViewAPISUSerializer.Meta):
        model = BenthicLITSUModel
        exclude = BaseSUViewAPISUSerializer.Meta.exclude.copy()
        exclude.append("location")
        header_order = BaseSUViewAPISUSerializer.Meta.header_order.copy()
        header_order.extend(
            [
                "label",
                "transect_number",
                "transect_len_surveyed",
                "total_length",
                "depth",
                "reef_slope",
                "percent_cover_benthic_category",
                "percent_cover_life_histories",
                "data_policy_benthiclit",
            ]
        )


class BenthicLITMethodSUGeoSerializer(BaseViewAPISUGeoSerializer):
    class Meta(BaseViewAPISUGeoSerializer.Meta):
        model = BenthicLITSUModel


class BenthicLITMethodSUCSVSerializer(ReportSerializer):
    fields = [
        ReportField("project_name", "Project name"),
        ReportField("project_admins", "Project admins", to_names),
        ReportField("country_name", "Country"),
        ReportField("contact_link", "Project contact link"),
        ReportField("tags", "Project organizations", to_names),
        ReportField("site_name", "Site"),
        ReportField("location", "Latitude", to_latitude, alias="latitude"),
        ReportField("location", "Longitude", to_longitude, alias="longitude"),
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
        ReportField("total_length", "Total cm"),
        ReportField("observers", "Observers", to_names),
        ReportField("percent_cover_benthic_category", "Percent cover by benthic category"),
        ReportField("percent_cover_life_histories", "Percent cover by life history"),
        ReportField("site_notes", "Site notes"),
        ReportField("management_notes", "Management notes"),
        ReportField("sample_unit_notes", "Sample unit notes"),
        ReportField("project_notes", "Project notes"),
        ReportField("project_includes_gfcr", "Project includes GFCR"),
        ReportField("suggested_citation", "Suggested citation"),
        ReportField("data_policy_benthiclit", "Benthic LIT data policy"),
        ReportField("site_id"),
    ]

    additional_fields = [
        ReportField("project_id"),
        ReportField("country_id"),
        ReportField("management_id"),
        ReportField("sample_event_id"),
        ReportField("sample_unit_ids"),
    ]


class BenthicLITMethodSESerializer(BaseSUViewAPISerializer):
    class Meta(BaseSUViewAPISerializer.Meta):
        model = BenthicLITSEModel
        exclude = BaseSUViewAPISerializer.Meta.exclude.copy()
        exclude.append("location")
        header_order = BaseSUViewAPISerializer.Meta.header_order.copy()
        header_order.extend(
            [
                "data_policy_benthiclit",
                "sample_unit_count",
                "depth_avg",
                "depth_sd",
                "percent_cover_benthic_category_avg",
                "percent_cover_benthic_category_sd",
                "percent_cover_life_histories_avg",
                "percent_cover_life_histories_sd",
            ]
        )


class BenthicLITMethodSEGeoSerializer(BaseViewAPIGeoSerializer):
    class Meta(BaseViewAPIGeoSerializer.Meta):
        model = BenthicLITSEModel


class BenthicLITMethodSECSVSerializer(ReportSerializer):
    fields = [
        ReportField("project_name", "Project name"),
        ReportField("project_admins", "Project admins", to_names),
        ReportField("country_name", "Country"),
        ReportField("contact_link", "Project contact link"),
        ReportField("tags", "Project organizations", to_names),
        ReportField("site_name", "Site"),
        ReportField("location", "Latitude", to_latitude, alias="latitude"),
        ReportField("location", "Longitude", to_longitude, alias="longitude"),
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
        ReportField("observers", "Observers", to_names),
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
        ReportField("project_includes_gfcr", "Project includes GFCR"),
        ReportField("suggested_citation", "Suggested citation"),
        ReportField("data_policy_benthiclit", "Benthic LIT data policy"),
        ReportField("site_id"),
    ]

    additional_fields = [
        ReportField("id"),
        ReportField("project_id"),
        ReportField("country_id"),
        ReportField("management_id"),
        ReportField("sample_event_id"),
    ]


class BenthicLITMethodObsFilterSet(BaseSUObsFilterSet):
    transect_len_surveyed = RangeFilter()
    reef_slope = BaseInFilter(method="char_lookup")
    transect_number = BaseInFilter(method="char_lookup")
    benthic_category = BaseInFilter(method="char_lookup")
    benthic_attribute = BaseInFilter(method="char_lookup")
    growth_form = BaseInFilter(method="char_lookup")
    length = RangeFilter()

    class Meta:
        model = BenthicLITObsModel
        fields = [
            "transect_len_surveyed",
            "reef_slope",
            "transect_number",
            "length",
            "benthic_category",
            "benthic_attribute",
            "growth_form",
        ]


class BenthicLITMethodObsSQLFilterSet(BenthicLITMethodObsFilterSet):
    class Meta(BenthicLITMethodObsFilterSet.Meta):
        model = BenthicLITObsSQLModel


class BenthicLITMethodSUFilterSet(BaseSUObsFilterSet):
    transect_len_surveyed = RangeFilter()
    reef_slope = BaseInFilter(method="char_lookup")
    transect_number = BaseInFilter(method="char_lookup")

    class Meta:
        model = BenthicLITSUModel
        fields = [
            "transect_len_surveyed",
            "reef_slope",
            "transect_number",
        ]


class BenthicLITMethodSUSQLFilterSet(BenthicLITMethodSUFilterSet):
    class Meta(BenthicLITMethodSUFilterSet.Meta):
        model = BenthicLITSUSQLModel


class BenthicLITMethodSEFilterSet(BaseSEFilterSet):
    sample_unit_count = RangeFilter()
    depth_avg = RangeFilter()

    class Meta:
        model = BenthicLITSEModel
        fields = ["sample_unit_count", "depth_avg"]


class BenthicLITMethodSESQLFilterSet(BenthicLITMethodSEFilterSet):
    class Meta(BenthicLITMethodSEFilterSet.Meta):
        model = BenthicLITSESQLModel


class BenthicLITProjectMethodObsView(BaseProjectMethodView):
    drf_label = "benthiclit-obs"
    project_policy = "data_policy_benthiclit"
    model = BenthicLITObsModel
    serializer_class = BenthicLITMethodObsSerializer
    serializer_class_geojson = BenthicLITMethodObsGeoSerializer
    serializer_class_csv = ObsBenthicLITCSVSerializer
    filterset_class = BenthicLITMethodObsFilterSet
    order_by = ("site_name", "sample_date", "transect_number", "label", "id")


class BenthicLITProjectMethodSUView(BaseProjectMethodView):
    drf_label = "benthiclit-su"
    project_policy = "data_policy_benthiclit"
    model = BenthicLITSUModel
    serializer_class = BenthicLITMethodSUSerializer
    serializer_class_geojson = BenthicLITMethodSUGeoSerializer
    serializer_class_csv = BenthicLITMethodSUCSVSerializer
    filterset_class = BenthicLITMethodSUFilterSet
    order_by = ("site_name", "sample_date", "transect_number")


class BenthicLITProjectMethodSEView(BaseProjectMethodView):
    drf_label = "benthiclit-se"
    project_policy = "data_policy_benthiclit"
    permission_classes = [Or(ProjectDataReadOnlyPermission, ProjectPublicSummaryPermission)]
    model = BenthicLITSEModel
    serializer_class = BenthicLITMethodSESerializer
    serializer_class_geojson = BenthicLITMethodSEGeoSerializer
    serializer_class_csv = BenthicLITMethodSECSVSerializer
    filterset_class = BenthicLITMethodSEFilterSet
    order_by = ("site_name", "sample_date")
