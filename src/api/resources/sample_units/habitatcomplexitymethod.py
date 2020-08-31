from django.db import transaction
from django_filters import BaseInFilter, RangeFilter
from rest_condition import Or
from rest_framework import status
from rest_framework.response import Response
from rest_framework.serializers import SerializerMethodField

from ...models.mermaid import HabitatComplexity, Project
from ...models.view_models import (
    HabitatComplexityObsView,
    HabitatComplexitySEView,
    HabitatComplexitySUView,
)
from ...permissions import ProjectDataReadOnlyPermission, ProjectPublicSummaryPermission
from ...reports.fields import ReportField
from ...reports.formatters import (
    to_day,
    to_governance,
    to_latitude,
    to_longitude,
    to_month,
    to_observers,
    to_str,
    to_year,
)
from ...reports.report_serializer import ReportSerializer
from ..base import (
    BaseProjectApiViewSet,
    BaseTransectFilterSet,
    BaseViewAPIGeoSerializer,
    BaseViewAPISerializer,
)
from ..benthic_transect import BenthicTransectSerializer
from ..habitat_complexity import HabitatComplexitySerializer
from ..obs_habitat_complexity import ObsHabitatComplexitySerializer
from ..observer import ObserverSerializer
from ..sample_event import SampleEventSerializer
from . import BaseProjectMethodView, save_model, save_one_to_many


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


class ObsHabitatComplexityCSVSerializer(ReportSerializer):
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
        ReportField("observers", "Observers", to_observers),
        ReportField("interval", "Interval (m)"),
        ReportField("score", "Habitat complexity value"),
        ReportField("score_name", "Habitat complexity name"),
        ReportField("site_notes", "Site notes"),
        ReportField("sample_event_notes", "Sampling event notes"),
        ReportField("management_notes", "Management notes"),
        ReportField("observation_notes", "Observation notes"),
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
        ReportField("data_policy_habitatcomplexity"),
        ReportField("relative_depth"),
    ]


class HabitatComplexityMethodView(BaseProjectApiViewSet):
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

            transaction.savepoint_commit(sid)

            habitat_complexity = HabitatComplexity.objects.get(id=habitat_complexity_id)
            return Response(
                HabitatComplexityMethodSerializer(habitat_complexity).data,
                status=status.HTTP_200_OK,
            )

        except:
            transaction.savepoint_rollback(sid)
            raise


class HabitatComplexityMethodObsSerializer(BaseViewAPISerializer):
    class Meta(BaseViewAPISerializer.Meta):
        model = HabitatComplexityObsView
        exclude = BaseViewAPISerializer.Meta.exclude.copy()
        exclude.append("location")
        header_order = ["id"] + BaseViewAPISerializer.Meta.header_order.copy()
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
                "observation_notes",
            ]
        )


class HabitatComplexityMethodObsGeoSerializer(BaseViewAPIGeoSerializer):
    class Meta(BaseViewAPIGeoSerializer.Meta):
        model = HabitatComplexityObsView


class HabitatComplexityMethodSUSerializer(BaseViewAPISerializer):
    class Meta(BaseViewAPISerializer.Meta):
        model = HabitatComplexitySUView
        exclude = BaseViewAPISerializer.Meta.exclude.copy()
        exclude.append("location")
        header_order = BaseViewAPISerializer.Meta.header_order.copy()
        header_order.extend(
            [
                "transect_number",
                "transect_len_surveyed",
                "depth",
                "reef_slope",
                "score_avg",
                "data_policy_habitatcomplexity",
            ]
        )


class HabitatComplexityMethodSUCSVSerializer(HabitatComplexityMethodSUSerializer):
    observers = SerializerMethodField()


class HabitatComplexityMethodSUGeoSerializer(BaseViewAPIGeoSerializer):
    class Meta(BaseViewAPIGeoSerializer.Meta):
        model = HabitatComplexitySUView


class HabitatComplexityMethodSESerializer(BaseViewAPISerializer):
    class Meta(BaseViewAPISerializer.Meta):
        model = HabitatComplexitySEView
        exclude = BaseViewAPISerializer.Meta.exclude.copy()
        exclude.append("location")
        header_order = BaseViewAPISerializer.Meta.header_order.copy()
        header_order.extend(
            [
                "data_policy_habitatcomplexity",
                "sample_unit_count",
                "depth_avg",
                "score_avg_avg",
            ]
        )


class HabitatComplexityMethodSEGeoSerializer(BaseViewAPIGeoSerializer):
    class Meta(BaseViewAPIGeoSerializer.Meta):
        model = HabitatComplexitySEView


class HabitatComplexityMethodObsFilterSet(BaseTransectFilterSet):
    depth = RangeFilter()
    sample_unit_id = BaseInFilter(method="id_lookup")
    observers = BaseInFilter(method="json_name_lookup")
    transect_len_surveyed = RangeFilter()
    reef_slope = BaseInFilter(method="char_lookup")
    interval = RangeFilter()

    class Meta:
        model = HabitatComplexityObsView
        fields = [
            "depth",
            "sample_unit_id",
            "observers",
            "transect_len_surveyed",
            "reef_slope",
            "transect_number",
            "interval",
            "score",
            "data_policy_habitatcomplexity",
        ]


class HabitatComplexityMethodSUFilterSet(BaseTransectFilterSet):
    transect_len_surveyed = RangeFilter()
    depth = RangeFilter()
    observers = BaseInFilter(method="json_name_lookup")
    reef_slope = BaseInFilter(method="char_lookup")
    interval_size = RangeFilter()

    class Meta:
        model = HabitatComplexitySUView
        fields = [
            "depth",
            "observers",
            "transect_len_surveyed",
            "reef_slope",
            "transect_number",
            "score_avg",
            "data_policy_habitatcomplexity",
        ]


class HabitatComplexityMethodSEFilterSet(BaseTransectFilterSet):
    sample_unit_count = RangeFilter()
    depth_avg = RangeFilter()
    score_avg_avg = RangeFilter()

    class Meta:
        model = HabitatComplexitySEView
        fields = [
            "sample_unit_count",
            "depth_avg",
            "data_policy_habitatcomplexity",
            "score_avg_avg",
        ]


class HabitatComplexityProjectMethodObsView(BaseProjectMethodView):
    drf_label = "habitatcomplexity-obs"
    project_policy = "data_policy_habitatcomplexity"
    serializer_class = HabitatComplexityMethodObsSerializer
    serializer_class_geojson = HabitatComplexityMethodObsGeoSerializer
    serializer_class_csv = ObsHabitatComplexityCSVSerializer
    filterset_class = HabitatComplexityMethodObsFilterSet
    queryset = HabitatComplexityObsView.objects.exclude(
        # project_status=Project.TEST
    )
    order_by = ("site_name", "sample_date", "transect_number", "label", "interval")


class HabitatComplexityProjectMethodSUView(BaseProjectMethodView):
    drf_label = "habitatcomplexity-su"
    project_policy = "data_policy_habitatcomplexity"
    serializer_class = HabitatComplexityMethodSUSerializer
    serializer_class_geojson = HabitatComplexityMethodSUGeoSerializer
    serializer_class_csv = HabitatComplexityMethodSUCSVSerializer
    filterset_class = HabitatComplexityMethodSUFilterSet
    queryset = HabitatComplexitySUView.objects.exclude(
        project_status=Project.TEST
    ).order_by("site_name", "sample_date", "transect_number")


class HabitatComplexityProjectMethodSEView(BaseProjectMethodView):
    drf_label = "habitatcomplexity-se"
    project_policy = "data_policy_habitatcomplexity"
    permission_classes = [
        Or(ProjectDataReadOnlyPermission, ProjectPublicSummaryPermission)
    ]
    serializer_class = HabitatComplexityMethodSESerializer
    serializer_class_geojson = HabitatComplexityMethodSEGeoSerializer
    serializer_class_csv = HabitatComplexityMethodSESerializer
    filterset_class = HabitatComplexityMethodSEFilterSet
    queryset = HabitatComplexitySEView.objects.exclude(
        project_status=Project.TEST
    ).order_by("site_name", "sample_date")
