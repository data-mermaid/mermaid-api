from django.db import transaction
from django_filters import BaseInFilter, RangeFilter
from rest_condition import Or
from rest_framework import status
from rest_framework.response import Response
from rest_framework.serializers import SerializerMethodField

# from .. import fieldreport
from ...models.mermaid import BenthicAttribute, BenthicPIT, Project
from ...models.view_models import BenthicPITObsView, BenthicPITSEView, BenthicPITSUView
from ...permissions import ProjectDataReadOnlyPermission, ProjectPublicSummaryPermission
from ...reports.fields import ReportField
from ...reports.formatters import (
    to_aca_benthic_covarite,
    to_aca_geomorphic_covarite,
    to_day,
    to_governance,
    to_latitude,
    to_longitude,
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
)
from ..benthic_pit import BenthicPITSerializer
from ..benthic_transect import BenthicTransectSerializer
from ..obs_benthic_pit import ObsBenthicPITSerializer
from ..observer import ObserverSerializer
from ..sample_event import SampleEventSerializer
from . import BaseProjectMethodView, save_model, save_one_to_many


class BenthicPITMethodSerializer(BenthicPITSerializer):
    sample_event = SampleEventSerializer(source="transect.sample_event")
    benthic_transect = BenthicTransectSerializer(source="transect")
    observers = ObserverSerializer(many=True)
    obs_benthic_pits = ObsBenthicPITSerializer(many=True, source="obsbenthicpit_set")

    class Meta:
        model = BenthicPIT
        exclude = []


class BenthicPITMethodView(BaseProjectApiViewSet):
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
        benthic_pit_data = {
            k: v for k, v in request.data.items() if k not in nested_data
        }
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

            transaction.savepoint_commit(sid)

            benthic_pit = BenthicPIT.objects.get(id=benthic_pit_id)
            return Response(
                BenthicPITMethodSerializer(benthic_pit).data, status=status.HTTP_200_OK
            )

        except:
            transaction.savepoint_rollback(sid)
            raise


class ObsBenthicPITCSVSerializer(ReportSerializer):
    fields = [
        ReportField("project_name", "Project name"),
        ReportField("country_name", "Country"),
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
        ReportField("management_compliance", "Estimated compliance",),
        ReportField("management_rules", "Management rules"),
        ReportField("transect_number", "Transect number"),
        ReportField("label", "Transect label"),
        ReportField("transect_len_surveyed", "Transect length surveyed"),
        ReportField("observers", "Observers", to_names),
        ReportField("interval", "PIT interval (m)"),
        ReportField("benthic_category", "Benthic category"),
        ReportField("benthic_attribute", "Benthic attribute"),
        ReportField("growth_form", "Growth form"),
        ReportField("site_notes", "Site notes"),
        ReportField("sample_event_notes", "Sampling event notes"),
        ReportField("management_notes", "Management notes"),
        ReportField("observation_notes", "Observation notes"),
        ReportField(
            "covariates",
            "ACA benthic class",
            to_aca_benthic_covarite,
            alias="aca_benthic"
        ),
        ReportField(
            "covariates",
            "ACA geomorphic class",
            to_aca_geomorphic_covarite,
            alias="aca_geomorphic"
        ),
    ]

    additional_fields = [
        ReportField("id"),
        ReportField("project_id"),
        ReportField("project_notes"),
        ReportField("site_id"),
        ReportField("contact_link"),
        ReportField("tags"),
        ReportField("country_id"),
        ReportField("management_id"),
        ReportField("sample_unit_id"),
        ReportField("interval_size"),
        ReportField("interval_start"),
        ReportField("data_policy_benthicpit"),
        ReportField("relative_depth"),
    ]


class BenthicPITMethodObsSerializer(BaseSUViewAPISerializer):
    class Meta(BaseSUViewAPISerializer.Meta):
        model = BenthicPITObsView
        exclude = BaseSUViewAPISerializer.Meta.exclude.copy()
        exclude.append("location")
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
                "observation_notes",
                "percent_cover_by_benthic_category",
            ]
        )


class BenthicPITMethodObsGeoSerializer(BaseViewAPIGeoSerializer):
    class Meta(BaseViewAPIGeoSerializer.Meta):
        model = BenthicPITObsView


class BenthicPITMethodSUSerializer(BaseSUViewAPISerializer):
    class Meta(BaseSUViewAPISerializer.Meta):
        model = BenthicPITSUView
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
                "interval_size",
                "interval_start",
                "percent_cover_by_benthic_category",
                "data_policy_benthicpit",
            ]
        )


class BenthicPITMethodSUCSVSerializer(ReportSerializer):
    fields = [
        ReportField("project_name", "Project name"),
        ReportField("country_name", "Country"),
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
        ReportField("management_compliance", "Estimated compliance", ),
        ReportField("management_rules", "Management rules"),
        ReportField("transect_number", "Transect number"),
        ReportField("label", "Transect label"),
        ReportField("transect_len_surveyed", "Transect length surveyed"),
        ReportField("observers", "Observers", to_names),
        ReportField("interval_size", "Interval size"),
        ReportField("interval_start", "Interval start"),
        ReportField("percent_cover_by_benthic_category", "Percent cover by benthic category"),
        ReportField("site_notes", "Site notes"),
        ReportField("sample_event_notes", "Sampling event notes"),
        ReportField("management_notes", "Management notes"),
        ReportField(
            "covariates",
            "ACA benthic class",
            to_aca_benthic_covarite,
            alias="aca_benthic"
        ),
        ReportField(
            "covariates",
            "ACA geomorphic class",
            to_aca_geomorphic_covarite,
            alias="aca_geomorphic"
        ),
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
        ReportField("data_policy_benthicpit"),
    ]


class BenthicPITMethodSECSVSerializer(ReportSerializer):
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
        ReportField("tide_name", "Tide"),
        ReportField("visibility_name", "Visibility"),
        ReportField("current_name", "Current"),
        ReportField("depth_avg", "Depth average"),
        ReportField("management_name", "Management name"),
        ReportField("management_name_secondary", "Management secondary name"),
        ReportField("management_est_year", "Management year established"),
        ReportField("management_size", "Management size"),
        ReportField("management_parties", "Governance", to_governance),
        ReportField("management_compliance", "Estimated compliance", ),
        ReportField("management_rules", "Management rules"),
        ReportField("sample_unit_count", "Sample unit count"),
        ReportField("percent_cover_by_benthic_category_avg", "Percent cover by benthic category average"),
        ReportField("site_notes", "Site notes"),
        ReportField("sample_event_notes", "Sampling event notes"),
        ReportField("management_notes", "Management notes"),
        ReportField(
            "covariates",
            "ACA benthic class",
            to_aca_benthic_covarite,
            alias="aca_benthic"
        ),
        ReportField(
            "covariates",
            "ACA geomorphic class",
            to_aca_geomorphic_covarite,
            alias="aca_geomorphic"
        ),
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
        ReportField("data_policy_benthicpit"),
    ]


class BenthicPITMethodSUGeoSerializer(BaseViewAPIGeoSerializer):
    class Meta(BaseViewAPIGeoSerializer.Meta):
        model = BenthicPITSUView


class BenthicPITMethodSESerializer(BaseSUViewAPISerializer):
    class Meta(BaseSUViewAPISerializer.Meta):
        model = BenthicPITSEView
        exclude = BaseSUViewAPISerializer.Meta.exclude.copy()
        exclude.append("location")
        header_order = BaseSUViewAPISerializer.Meta.header_order.copy()
        header_order.extend(
            [
                "data_policy_benthicpit",
                "sample_unit_count",
                "depth_avg",
                "percent_cover_by_benthic_category_avg",
            ]
        )


class BenthicPITMethodSEGeoSerializer(BaseViewAPIGeoSerializer):
    class Meta(BaseViewAPIGeoSerializer.Meta):
        model = BenthicPITSEView


class BenthicPITMethodObsFilterSet(BaseSUObsFilterSet):
    transect_len_surveyed = RangeFilter()
    reef_slope = BaseInFilter(method="char_lookup")
    interval_size = RangeFilter()
    interval = RangeFilter()

    class Meta:
        model = BenthicPITObsView
        fields = [
            "transect_len_surveyed",
            "reef_slope",
            "transect_number",
            "interval_size",
            "interval",
            "benthic_category",
            "benthic_attribute",
            "growth_form",
            "data_policy_benthicpit",
        ]


class BenthicPITMethodSUFilterSet(BaseSUObsFilterSet):
    transect_len_surveyed = RangeFilter()
    reef_slope = BaseInFilter(method="char_lookup")
    interval_size = RangeFilter()

    class Meta:
        model = BenthicPITSUView
        fields = [
            "transect_len_surveyed",
            "reef_slope",
            "transect_number",
            "interval_size",
            "data_policy_benthicpit",
        ]


class BenthicPITMethodSEFilterSet(BaseSEFilterSet):
    sample_unit_count = RangeFilter()
    depth_avg = RangeFilter()

    class Meta:
        model = BenthicPITSEView
        fields = ["sample_unit_count", "depth_avg", "data_policy_benthicpit"]


class BenthicPITProjectMethodObsView(BaseProjectMethodView):
    drf_label = "benthicpit-obs"
    project_policy = "data_policy_benthicpit"
    serializer_class = BenthicPITMethodObsSerializer
    serializer_class_geojson = BenthicPITMethodObsGeoSerializer
    serializer_class_csv = ObsBenthicPITCSVSerializer
    filterset_class = BenthicPITMethodObsFilterSet
    queryset = BenthicPITObsView.objects.all()
    order_by = ("site_name", "sample_date", "transect_number", "label", "interval")


class BenthicPITProjectMethodSUView(BaseProjectMethodView):
    drf_label = "benthicpit-su"
    project_policy = "data_policy_benthicpit"
    serializer_class = BenthicPITMethodSUSerializer
    serializer_class_geojson = BenthicPITMethodSUGeoSerializer
    serializer_class_csv = BenthicPITMethodSUCSVSerializer
    filterset_class = BenthicPITMethodSUFilterSet
    queryset = BenthicPITSUView.objects.all()
    order_by = (
        "site_name", "sample_date", "transect_number"
    )


class BenthicPITProjectMethodSEView(BaseProjectMethodView):
    drf_label = "benthicpit-se"
    project_policy = "data_policy_benthicpit"
    permission_classes = [
        Or(ProjectDataReadOnlyPermission, ProjectPublicSummaryPermission)
    ]
    serializer_class = BenthicPITMethodSESerializer
    serializer_class_geojson = BenthicPITMethodSEGeoSerializer
    serializer_class_csv = BenthicPITMethodSECSVSerializer
    filterset_class = BenthicPITMethodSEFilterSet
    queryset = BenthicPITSEView.objects.all()
    order_by = (
        "site_name", "sample_date"
    )
