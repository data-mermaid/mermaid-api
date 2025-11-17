from django.db import transaction
from django_filters import BaseInFilter, RangeFilter
from rest_condition import Or
from rest_framework import status
from rest_framework.response import Response
from rest_framework.validators import UniqueTogetherValidator

from ...models import (
    BleachingQCColoniesBleachedObsModel,
    BleachingQCColoniesBleachedObsSQLModel,
    BleachingQCQuadratBenthicPercentObsModel,
    BleachingQCQuadratBenthicPercentObsSQLModel,
    BleachingQCSEModel,
    BleachingQCSESQLModel,
    BleachingQCSUModel,
    BleachingQCSUSQLModel,
    BleachingQuadratCollection,
    ObsColoniesBleached,
    ObsQuadratBenthicPercent,
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
    to_yesno,
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
from ..mixins import SampleUnitMethodEditMixin, SampleUnitMethodSummaryReport
from ..observer import ObserverSerializer
from ..quadrat_collection import QuadratCollectionSerializer
from ..sample_event import SampleEventSerializer
from . import (
    BaseProjectMethodView,
    clean_sample_event_models,
    save_model,
    save_one_to_many,
)


class BleachingQuadratCollectionSerializer(BaseAPISerializer):
    class Meta:
        model = BleachingQuadratCollection
        exclude = []
        extra_kwargs = {}


class ObsColoniesBleachedSerializer(BaseAPISerializer):
    class Meta:
        model = ObsColoniesBleached
        exclude = []
        extra_kwargs = {
            "attribute": {
                "error_messages": {
                    "does_not_exist": 'Benthic attribute with id "{pk_value}", does not exist.'
                }
            }
        }


class ObsQuadratBenthicPercentSerializer(BaseAPISerializer):
    class Meta:
        model = ObsQuadratBenthicPercent
        exclude = []
        extra_kwargs = {
            "quadrat_number": {"error_messages": {"null": "Quadrat number is required"}}
        }
        validators = [
            UniqueTogetherValidator(
                queryset=ObsQuadratBenthicPercent.objects.all(),
                fields=["bleachingquadratcollection", "quadrat_number"],
                message="Duplicate quadrat numbers",
            )
        ]


class BleachingQuadratCollectionMethodSerializer(BleachingQuadratCollectionSerializer):
    sample_event = SampleEventSerializer(source="quadrat.sample_event")
    quadrat_collection = QuadratCollectionSerializer(source="quadrat")
    observers = ObserverSerializer(many=True)
    obs_quadrat_benthic_percent = ObsQuadratBenthicPercentSerializer(
        many=True, source="obsquadratbenthicpercent_set"
    )
    obs_colonies_bleached = ObsColoniesBleachedSerializer(
        many=True, source="obscoloniesbleached_set"
    )

    class Meta:
        model = BleachingQuadratCollection
        exclude = []


class BleachingQuadratCollectionMethodView(
    SampleUnitMethodSummaryReport, SampleUnitMethodEditMixin, BaseProjectApiViewSet
):
    queryset = BleachingQuadratCollection.objects.select_related(
        "quadrat", "quadrat__sample_event"
    ).all()
    serializer_class = BleachingQuadratCollectionMethodSerializer
    http_method_names = ["get", "put", "head", "delete"]

    @transaction.atomic
    def update(self, request, project_pk, pk=None):
        errors = {}
        is_valid = True
        nested_data = dict(
            sample_event=request.data.get("sample_event"),
            quadrat_collection=request.data.get("quadrat_collection"),
            observers=request.data.get("observers"),
            obs_quadrat_benthic_percent=request.data.get("obs_quadrat_benthic_percent"),
            obs_colonies_bleached=request.data.get("obs_colonies_bleached"),
        )
        bleaching_qc_data = {k: v for k, v in request.data.items() if k not in nested_data}
        bleaching_qc_id = bleaching_qc_data["id"]

        context = dict(request=request)

        # Save models in a transaction
        sid = transaction.savepoint()
        try:
            bleaching_qc = BleachingQuadratCollection.objects.get(id=bleaching_qc_id)

            # Observers
            check, errs = save_one_to_many(
                foreign_key=("transectmethod", bleaching_qc_id),
                database_records=bleaching_qc.observers.all(),
                data=request.data.get("observers") or [],
                serializer_class=ObserverSerializer,
                context=context,
            )
            if check is False:
                is_valid = False
                errors["observers"] = errs

            # Observations - Colonies Bleached
            check, errs = save_one_to_many(
                foreign_key=("bleachingquadratcollection", bleaching_qc_id),
                database_records=bleaching_qc.obscoloniesbleached_set.all(),
                data=request.data.get("obs_colonies_bleached") or [],
                serializer_class=ObsColoniesBleachedSerializer,
                context=context,
            )
            if check is False:
                is_valid = False
                errors["obs_colonies_bleached"] = errs

            # Observations - Quadrat Benthic Percent
            check, errs = save_one_to_many(
                foreign_key=("bleachingquadratcollection", bleaching_qc_id),
                database_records=bleaching_qc.obsquadratbenthicpercent_set.all(),
                data=request.data.get("obs_quadrat_benthic_percent") or [],
                serializer_class=ObsQuadratBenthicPercentSerializer,
                context=context,
            )
            if check is False:
                is_valid = False
                errors["obs_quadrat_benthic_percent"] = errs

            # Sample Event
            check, errs = save_model(
                data=nested_data["sample_event"],
                serializer_class=SampleEventSerializer,
                context=context,
            )
            if check is False:
                is_valid = False
                errors["sample_event"] = errs

            # Quadrat Collection
            check, errs = save_model(
                data=nested_data["quadrat_collection"],
                serializer_class=QuadratCollectionSerializer,
                context=context,
            )
            if check is False:
                is_valid = False
                errors["quadrat_collection"] = errs

            # Bleaching Quadrat Collection
            check, errs = save_model(
                data=bleaching_qc_data,
                serializer_class=BleachingQuadratCollectionSerializer,
                context=context,
            )
            if check is False:
                is_valid = False
                errors["bleaching_quadrat_collection"] = errs

            if is_valid is False:
                transaction.savepoint_rollback(sid)
                return Response(data=errors, status=status.HTTP_400_BAD_REQUEST)

            clean_sample_event_models(nested_data["sample_event"])

            transaction.savepoint_commit(sid)
            bleaching_qc = BleachingQuadratCollection.objects.get(id=bleaching_qc_id)
            return Response(
                BleachingQuadratCollectionMethodSerializer(bleaching_qc).data,
                status=status.HTTP_200_OK,
            )
        except:
            transaction.savepoint_rollback(sid)
            raise


class BleachingQCMethodObsColoniesBleachedSerializer(BaseSUViewAPISerializer):
    class Meta(BaseSUViewAPISerializer.Meta):
        model = BleachingQCColoniesBleachedObsModel
        exclude = BaseSUViewAPISerializer.Meta.exclude.copy()
        exclude.extend(["location", "observation_notes"])
        header_order = ["id"] + BaseSUViewAPISerializer.Meta.header_order.copy()
        header_order.extend(
            [
                "sample_unit_id",
                "sample_time",
                "label",
                "quadrat_size",
                "depth",
                "observers",
                "benthic_category",
                "benthic_attribute",
                "growth_form",
                "count_normal",
                "count_pale",
                "count_20",
                "count_50",
                "count_80",
                "count_100",
                "count_dead",
                "data_policy_bleachingqc",
                "life_histories",
            ]
        )


class BleachingQCMethodObsColoniesBleachedGeoSerializer(BaseViewAPIGeoSerializer):
    class Meta(BaseViewAPIGeoSerializer.Meta):
        model = BleachingQCColoniesBleachedObsModel


class ObsBleachingQCColoniesBleachedCSVSerializer(ReportSerializer):
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
        ReportField("quadrat_size", "Quadrat size"),
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
        ReportField("observers", "Observers", to_names),
        ReportField("label", "Quadrat collection label"),
        ReportField("benthic_category", "Benthic category"),
        ReportField("benthic_attribute", "Benthic attribute"),
        ReportField("growth_form", "Growth form"),
        ReportField("count_normal", "Normal count"),
        ReportField("count_pale", "Pale count"),
        ReportField("count_20", "0-20% bleached count"),
        ReportField("count_50", "20-50% bleached count"),
        ReportField("count_80", "50-80% bleached count"),
        ReportField("count_100", "80-100% bleached count"),
        ReportField("count_dead", "Recently dead count"),
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
        ReportField("project_includes_gfcr", "Project includes GFCR", to_yesno),
        ReportField("suggested_citation", "Suggested citation"),
        ReportField("data_policy_bleachingqc", "Bleaching data policy"),
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


class BleachingQCMethodObsQuadratBenthicPercentSerializer(BaseSUViewAPISerializer):
    class Meta(BaseSUViewAPISerializer.Meta):
        model = BleachingQCQuadratBenthicPercentObsModel
        exclude = BaseSUViewAPISerializer.Meta.exclude.copy()
        exclude.extend(["location", "observation_notes"])
        header_order = ["id"] + BaseSUViewAPISerializer.Meta.header_order.copy()
        header_order.extend(
            [
                "sample_unit_id",
                "sample_time",
                "label",
                "quadrat_size",
                "depth",
                "observers",
                "quadrat_number",
                "percent_hard",
                "percent_soft",
                "percent_algae",
                "data_policy_bleachingqc",
            ]
        )


class BleachingQCMethodObsQuadratBenthicPercentGeoSerializer(BaseViewAPIGeoSerializer):
    class Meta(BaseViewAPIGeoSerializer.Meta):
        model = BleachingQCQuadratBenthicPercentObsModel


class ObsQuadratBenthicPercentCSVSerializer(ReportSerializer):
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
        ReportField("quadrat_size", "Quadrat size"),
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
        ReportField("observers", "Observers", to_names),
        ReportField("label", "Quadrat collection label"),
        ReportField("quadrat_number", "Quadrat number"),
        ReportField("percent_hard", "Hard coral (% cover)"),
        ReportField("percent_soft", "Soft coral (% cover)"),
        ReportField("percent_algae", "Macroalgae (% cover)"),
        ReportField("site_notes", "Site notes"),
        ReportField("management_notes", "Management notes"),
        ReportField("sample_unit_notes", "Sample unit notes"),
        ReportField("project_notes", "Project notes"),
        ReportField("project_includes_gfcr", "Project includes GFCR", to_yesno),
        ReportField("suggested_citation", "Suggested citation"),
        ReportField("data_policy_bleachingqc", "Bleaching data policy"),
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


class BleachingQCMethodSUSerializer(BaseSUViewAPISUSerializer):
    class Meta(BaseSUViewAPISUSerializer.Meta):
        model = BleachingQCSUModel
        exclude = BaseSUViewAPISUSerializer.Meta.exclude.copy()
        exclude.append("location")
        header_order = BaseSUViewAPISUSerializer.Meta.header_order.copy()
        header_order.extend(
            [
                "label",
                "quadrat_size",
                "depth",
                "observers",
                "count_genera",
                "count_total",
                "percent_normal",
                "percent_pale",
                "percent_20",
                "percent_50",
                "percent_80",
                "percent_100",
                "percent_dead",
                "percent_bleached",
                "quadrat_count",
                "percent_hard_avg",
                "percent_hard_sd",
                "percent_soft_avg",
                "percent_soft_sd",
                "percent_algae_avg",
                "percent_algae_sd",
                "percent_cover_life_histories",
                "data_policy_bleachingqc",
            ]
        )


class BleachingQCMethodSUGeoSerializer(BaseViewAPISUGeoSerializer):
    class Meta(BaseViewAPISUGeoSerializer.Meta):
        model = BleachingQCSUModel


class BleachingQCMethodSUCSVSerializer(ReportSerializer):
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
        ReportField("quadrat_size", "Quadrat size"),
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
        ReportField("observers", "Observers", to_names),
        ReportField("label", "Transect label"),
        ReportField("count_genera", "Genera count"),
        ReportField("count_total", "Total count"),
        ReportField("percent_normal", "Percent normal"),
        ReportField("percent_pale", "Percent pale"),
        ReportField("percent_20", "Percent 0-20% bleached"),
        ReportField("percent_50", "Percent 20-50% bleached"),
        ReportField("percent_80", "Percent 50-80% bleached"),
        ReportField("percent_100", "Percent 80-100% bleached"),
        ReportField("percent_dead", "Percent recently dead"),
        ReportField("percent_bleached", "Percent bleached"),
        ReportField("quadrat_count", "Number of quadrats"),
        ReportField("percent_hard_avg", "Average Hard Coral (% cover)"),
        ReportField("percent_hard_sd", "Hard Coral (% cover) standard deviation"),
        ReportField("percent_soft_avg", "Average Soft Coral (% cover)"),
        ReportField("percent_soft_sd", "Soft Coral (% cover) standard deviation"),
        ReportField("percent_algae_avg", "Average Macroalgae (% cover)"),
        ReportField("percent_algae_sd", "Macroalgae (% cover) standard deviation"),
        ReportField("percent_cover_life_histories", "Percent cover by life history"),
        ReportField("site_notes", "Site notes"),
        ReportField("management_notes", "Management notes"),
        ReportField("sample_unit_notes", "Sample unit notes"),
        ReportField("project_notes", "Project notes"),
        ReportField("project_includes_gfcr", "Project includes GFCR", to_yesno),
        ReportField("suggested_citation", "Suggested citation"),
        ReportField("data_policy_bleachingqc", "Bleaching data policy"),
        ReportField("site_id"),
    ]

    additional_fields = [
        ReportField("project_id"),
        ReportField("country_id"),
        ReportField("management_id"),
        ReportField("sample_event_id"),
        ReportField("sample_unit_ids"),
    ]


class BleachingQCMethodSESerializer(BaseSUViewAPISerializer):
    class Meta(BaseSUViewAPISerializer.Meta):
        model = BleachingQCSEModel
        exclude = BaseSUViewAPISerializer.Meta.exclude.copy()
        exclude.append("location")
        header_order = BaseSUViewAPISerializer.Meta.header_order.copy()
        header_order.extend(
            [
                "sample_unit_count",
                "depth_avg",
                "depth_sd",
                "quadrat_size_avg",
                "count_total_avg",
                "count_total_sd",
                "count_genera_avg",
                "count_genera_sd",
                "percent_normal_avg",
                "percent_normal_sd",
                "percent_pale_avg",
                "percent_pale_sd",
                "percent_20_avg",
                "percent_20_sd",
                "percent_50_avg",
                "percent_50_sd",
                "percent_80_avg",
                "percent_80_sd",
                "percent_100_avg",
                "percent_100_sd",
                "percent_dead_avg",
                "percent_dead_sd",
                "percent_bleached_avg",
                "percent_bleached_sd",
                "quadrat_count_avg",
                "percent_hard_avg_avg",
                "percent_hard_avg_sd",
                "percent_soft_avg_avg",
                "percent_soft_avg_sd",
                "percent_algae_avg_avg",
                "percent_algae_avg_sd",
                "percent_cover_life_histories_avg",
                "percent_cover_life_histories_sd",
                "data_policy_bleachingqc",
            ]
        )


class BleachingQCMethodSEGeoSerializer(BaseViewAPIGeoSerializer):
    class Meta(BaseViewAPIGeoSerializer.Meta):
        model = BleachingQCSEModel


class BleachingQCMethodSECSVSerializer(ReportSerializer):
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
        ReportField("quadrat_size_avg", "Quadrat size average"),
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
        ReportField("count_total_avg", "Total count average"),
        ReportField("count_total_sd", "Total count standard deviation"),
        ReportField("count_genera_avg", "Genera count average"),
        ReportField("count_genera_sd", "Genera count standard deviation"),
        ReportField("percent_normal_avg", "Percent normal average"),
        ReportField("percent_normal_sd", "Percent normal standard deviation"),
        ReportField("percent_pale_avg", "Percent pale average"),
        ReportField("percent_pale_sd", "Percent pale standard deviation"),
        ReportField("percent_20_avg", "Percent 0-20% bleached average"),
        ReportField("percent_20_sd", "Percent 0-20% bleached standard deviation"),
        ReportField("percent_50_avg", "Percent 20-50% bleached average"),
        ReportField("percent_50_sd", "Percent 20-50% bleached standard deviation"),
        ReportField("percent_80_avg", "Percent 50%-80% bleached average"),
        ReportField("percent_80_sd", "Percent 50%-80% bleached standard deviation"),
        ReportField("percent_100_avg", "Percent 80-100% bleached average"),
        ReportField("percent_100_sd", "Percent 80-100% bleached standard deviation"),
        ReportField("percent_dead_avg", "Percent recently dead average"),
        ReportField("percent_dead_sd", "Percent recently dead standard deviation"),
        ReportField("percent_bleached_avg", "Percent bleached average"),
        ReportField("percent_bleached_sd", "Percent bleached standard deviation"),
        ReportField("quadrat_count_avg", "Number of quadrats average"),
        ReportField("percent_hard_avg_avg", "Average Hard Coral (% cover) average"),
        ReportField("percent_hard_avg_sd", "Average Hard Coral (% cover) standard deviation"),
        ReportField("percent_soft_avg_avg", "Average Soft Coral (% cover) average"),
        ReportField("percent_soft_avg_sd", "Average Soft Coral (% cover) standard deviation"),
        ReportField("percent_algae_avg_avg", "Average Macroalgae (% cover) average"),
        ReportField("percent_algae_avg_sd", "Average Macroalgae (% cover) standard deviation"),
        ReportField("percent_cover_life_histories_avg", "Percent cover by life history average"),
        ReportField(
            "percent_cover_life_histories_sd", "Percent cover by life history standard deviation"
        ),
        ReportField("site_notes", "Site notes"),
        ReportField("management_notes", "Management notes"),
        ReportField("project_notes", "Project notes"),
        ReportField("project_includes_gfcr", "Project includes GFCR", to_yesno),
        ReportField("suggested_citation", "Suggested citation"),
        ReportField("data_policy_bleachingqc", "Bleaching data policy"),
        ReportField("site_id"),
    ]

    additional_fields = [
        ReportField("id"),
        ReportField("project_id"),
        ReportField("country_id"),
        ReportField("management_id"),
        ReportField("sample_event_id"),
    ]


class BleachingQCMethodColoniesBleachedObsFilterSet(BaseSUObsFilterSet):
    benthic_attribute = BaseInFilter(method="char_lookup")
    growth_form = BaseInFilter(method="char_lookup")
    count_normal = RangeFilter()
    count_pale = RangeFilter()
    count_20 = RangeFilter()
    count_50 = RangeFilter()
    count_80 = RangeFilter()
    count_100 = RangeFilter()
    count_dead = RangeFilter()

    class Meta:
        model = BleachingQCColoniesBleachedObsModel
        fields = [
            "quadrat_size",
            "benthic_attribute",
            "growth_form",
            "count_normal",
            "count_pale",
            "count_20",
            "count_50",
            "count_80",
            "count_100",
            "count_dead",
        ]


class BleachingQCMethodColoniesBleachedObsSQLFilterSet(
    BleachingQCMethodColoniesBleachedObsFilterSet
):
    class Meta(BleachingQCMethodColoniesBleachedObsFilterSet.Meta):
        model = BleachingQCColoniesBleachedObsSQLModel


class BleachingQCMethodQuadratBenthicPercentObsFilterSet(BaseSUObsFilterSet):
    percent_hard = RangeFilter()
    percent_soft = RangeFilter()
    percent_algae = RangeFilter()

    class Meta:
        model = BleachingQCQuadratBenthicPercentObsModel
        fields = [
            "quadrat_size",
            "quadrat_number",
            "percent_hard",
            "percent_soft",
            "percent_algae",
        ]


class BleachingQCMethodQuadratBenthicPercentObsSQLFilterSet(
    BleachingQCMethodQuadratBenthicPercentObsFilterSet
):
    class Meta(BleachingQCMethodQuadratBenthicPercentObsFilterSet.Meta):
        model = BleachingQCQuadratBenthicPercentObsSQLModel


class BleachingQCMethodSUFilterSet(BaseSUObsFilterSet):
    count_genera = RangeFilter()
    count_total = RangeFilter()
    percent_normal = RangeFilter()
    percent_pale = RangeFilter()
    percent_20 = RangeFilter()
    percent_50 = RangeFilter()
    percent_80 = RangeFilter()
    percent_100 = RangeFilter()
    percent_dead = RangeFilter()
    percent_bleached = RangeFilter()
    quadrat_count = RangeFilter()
    percent_hard_avg = RangeFilter()
    percent_soft_avg = RangeFilter()
    percent_algae_avg = RangeFilter()

    class Meta:
        model = BleachingQCSUModel
        fields = [
            "quadrat_size",
            "count_genera",
            "count_total",
            "percent_normal",
            "percent_pale",
            "percent_20",
            "percent_50",
            "percent_80",
            "percent_100",
            "percent_dead",
            "percent_bleached",
            "quadrat_count",
            "percent_hard_avg",
            "percent_soft_avg",
            "percent_algae_avg",
        ]


class BleachingQCMethodSUSQLFilterSet(BleachingQCMethodSUFilterSet):
    class Meta(BleachingQCMethodSUFilterSet.Meta):
        model = BleachingQCSUSQLModel


class BleachingQCMethodSEFilterSet(BaseSEFilterSet):
    sample_unit_count = RangeFilter()
    depth_avg = RangeFilter()
    quadrat_size_avg = RangeFilter()
    count_total_avg = RangeFilter()
    count_genera_avg = RangeFilter()
    percent_normal_avg = RangeFilter()
    percent_pale_avg = RangeFilter()
    percent_20_avg = RangeFilter()
    percent_50_avg = RangeFilter()
    percent_80_avg = RangeFilter()
    percent_100_avg = RangeFilter()
    percent_dead_avg = RangeFilter()
    percent_bleached_avg = RangeFilter()
    quadrat_count_avg = RangeFilter()
    percent_hard_avg_avg = RangeFilter()
    percent_soft_avg_avg = RangeFilter()
    percent_algae_avg_avg = RangeFilter()

    class Meta:
        model = BleachingQCSEModel
        fields = [
            "sample_unit_count",
            "depth_avg",
            "quadrat_size_avg",
            "count_total_avg",
            "count_genera_avg",
            "percent_normal_avg",
            "percent_pale_avg",
            "percent_20_avg",
            "percent_50_avg",
            "percent_80_avg",
            "percent_100_avg",
            "percent_dead_avg",
            "percent_bleached_avg",
            "quadrat_count_avg",
            "percent_hard_avg_avg",
            "percent_soft_avg_avg",
            "percent_algae_avg_avg",
        ]


class BleachingQCMethodSESQLFilterSet(BleachingQCMethodSEFilterSet):
    class Meta(BleachingQCMethodSEFilterSet.Meta):
        model = BleachingQCSESQLModel


class BleachingQCProjectMethodObsColoniesBleachedView(BaseProjectMethodView):
    drf_label = "bleachingqc-obscoloniesbleached"
    project_policy = "data_policy_bleachingqc"
    model = BleachingQCColoniesBleachedObsModel
    serializer_class = BleachingQCMethodObsColoniesBleachedSerializer
    serializer_class_geojson = BleachingQCMethodObsColoniesBleachedGeoSerializer
    serializer_class_csv = ObsBleachingQCColoniesBleachedCSVSerializer
    filterset_class = BleachingQCMethodColoniesBleachedObsFilterSet
    ordering = ["site_name", "sample_date", "label", "benthic_attribute", "growth_form"]
    ordering_fields = ordering


class BleachingQCProjectMethodObsQuadratBenthicPercentView(BaseProjectMethodView):
    drf_label = "bleachingqc-obsquadratbenthicpercent"
    project_policy = "data_policy_bleachingqc"
    model = BleachingQCQuadratBenthicPercentObsModel
    serializer_class = BleachingQCMethodObsQuadratBenthicPercentSerializer
    serializer_class_geojson = BleachingQCMethodObsQuadratBenthicPercentGeoSerializer
    serializer_class_csv = ObsQuadratBenthicPercentCSVSerializer
    filterset_class = BleachingQCMethodQuadratBenthicPercentObsFilterSet
    ordering = ["site_name", "sample_date", "label", "quadrat_number"]
    ordering_fields = ordering


class BleachingQCProjectMethodSUView(BaseProjectMethodView):
    drf_label = "bleachingqc-su"
    project_policy = "data_policy_bleachingqc"
    model = BleachingQCSUModel
    serializer_class = BleachingQCMethodSUSerializer
    serializer_class_geojson = BleachingQCMethodSUGeoSerializer
    serializer_class_csv = BleachingQCMethodSUCSVSerializer
    filterset_class = BleachingQCMethodSUFilterSet
    ordering = ["site_name", "sample_date", "label"]
    ordering_fields = ordering


class BleachingQCProjectMethodSEView(BaseProjectMethodView):
    drf_label = "bleachingqc-se"
    project_policy = "data_policy_bleachingqc"
    permission_classes = [Or(ProjectDataReadOnlyPermission, ProjectPublicSummaryPermission)]
    model = BleachingQCSEModel
    serializer_class = BleachingQCMethodSESerializer
    serializer_class_geojson = BleachingQCMethodSEGeoSerializer
    serializer_class_csv = BleachingQCMethodSECSVSerializer
    filterset_class = BleachingQCMethodSEFilterSet
    ordering = ["site_name", "sample_date"]
    ordering_fields = ordering
