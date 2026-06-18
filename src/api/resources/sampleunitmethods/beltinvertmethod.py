from decimal import Decimal

from django.db import transaction
from django_filters import RangeFilter
from rest_condition import Or
from rest_framework import serializers, status
from rest_framework.response import Response

from ...models import (
    BeltInvert,
    BeltInvertObsModel,
    BeltInvertObsSQLModel,
    BeltInvertSEModel,
    BeltInvertSESQLModel,
    BeltInvertSUModel,
    BeltInvertSUSQLModel,
    ObsBeltInvert,
)
from ...permissions import ProjectDataReadOnlyPermission, ProjectPublicSummaryPermission
from ...reports.fields import ReportField
from ...reports.formatters import (
    to_day,
    to_governance,
    to_join_list,
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
from ..invert_belt_transect import InvertBeltTransectSerializer
from ..mixins import SampleUnitMethodEditMixin, SampleUnitMethodSummaryReport
from ..observer import ObserverSerializer
from ..sample_event import SampleEventSerializer
from . import (
    BaseProjectMethodView,
    clean_sample_event_models,
    save_model,
    save_one_to_many,
)

__all__ = ["BeltInvertSerializer", "ObsBeltInvertSerializer"]


class BeltInvertSerializer(BaseAPISerializer):
    class Meta:
        model = BeltInvert
        exclude = []


class ObsBeltInvertSerializer(BaseAPISerializer):
    size = serializers.DecimalField(
        max_digits=5,
        decimal_places=1,
        coerce_to_string=False,
        allow_null=True,
        required=False,
        min_value=Decimal("0.1"),
    )

    class Meta:
        model = ObsBeltInvert
        exclude = []
        extra_kwargs = {
            "invert_attribute": {
                "error_messages": {
                    "does_not_exist": 'Invert attribute with id "{pk_value}", does not exist.'
                }
            }
        }


class BeltInvertMethodSerializer(BeltInvertSerializer):
    sample_event = SampleEventSerializer(source="transect.sample_event")
    beltinvert_transect = InvertBeltTransectSerializer(source="transect")
    observers = ObserverSerializer(many=True)
    obs_belt_inverts = ObsBeltInvertSerializer(many=True, source="beltinvert_observations")

    class Meta:
        model = BeltInvert
        exclude = []


class BeltInvertMethodView(
    SampleUnitMethodSummaryReport, SampleUnitMethodEditMixin, BaseProjectApiViewSet
):
    project_policy = "data_policy_macroinvertebrate"
    queryset = (
        BeltInvert.objects.select_related("transect", "transect__sample_event")
        .all()
        .order_by("updated_on", "id")
    )
    serializer_class = BeltInvertMethodSerializer
    http_method_names = ["get", "put", "head", "delete"]

    @transaction.atomic
    def update(self, request, project_pk, pk=None):
        errors = {}
        is_valid = True
        nested_data = dict(
            sample_event=request.data.get("sample_event"),
            beltinvert_transect=request.data.get("beltinvert_transect"),
            observers=request.data.get("observers"),
            obs_belt_inverts=request.data.get("obs_belt_inverts"),
        )
        belt_invert_data = {k: v for k, v in request.data.items() if k not in nested_data}
        belt_invert_id = belt_invert_data["id"]

        context = dict(request=request)

        sid = transaction.savepoint()
        try:
            try:
                belt_invert = BeltInvert.objects.get(
                    id=belt_invert_id,
                    transect__sample_event__site__project_id=project_pk,
                )
            except BeltInvert.DoesNotExist:
                transaction.savepoint_rollback(sid)
                return Response(status=status.HTTP_404_NOT_FOUND)

            check, errs = save_one_to_many(
                foreign_key=("transectmethod", belt_invert_id),
                database_records=belt_invert.observers.all(),
                data=request.data.get("observers") or [],
                serializer_class=ObserverSerializer,
                context=context,
            )
            if check is False:
                is_valid = False
                errors["observers"] = errs

            check, errs = save_one_to_many(
                foreign_key=("beltinvert", belt_invert_id),
                database_records=belt_invert.beltinvert_observations.all(),
                data=request.data.get("obs_belt_inverts") or [],
                serializer_class=ObsBeltInvertSerializer,
                context=context,
            )
            if check is False:
                is_valid = False
                errors["obs_belt_inverts"] = errs

            check, errs = save_model(
                data=nested_data["sample_event"],
                serializer_class=SampleEventSerializer,
                context=context,
            )
            if check is False:
                is_valid = False
                errors["sample_event"] = errs

            check, errs = save_model(
                data=nested_data["beltinvert_transect"],
                serializer_class=InvertBeltTransectSerializer,
                context=context,
            )
            if check is False:
                is_valid = False
                errors["beltinvert_transect"] = errs

            check, errs = save_model(
                data=belt_invert_data,
                serializer_class=BeltInvertSerializer,
                context=context,
            )
            if check is False:
                is_valid = False
                errors["belt_invert"] = errs

            if is_valid is False:
                transaction.savepoint_rollback(sid)
                return Response(data=errors, status=status.HTTP_400_BAD_REQUEST)

            clean_sample_event_models(nested_data["sample_event"])

            transaction.savepoint_commit(sid)

            belt_invert = BeltInvert.objects.get(id=belt_invert_id)
            return Response(BeltInvertMethodSerializer(belt_invert).data, status=status.HTTP_200_OK)

        except Exception:
            transaction.savepoint_rollback(sid)
            raise


class BeltInvertMethodObsSerializer(BaseSUViewAPISerializer):
    class Meta(BaseSUViewAPISerializer.Meta):
        model = BeltInvertObsModel
        exclude = BaseSUViewAPISerializer.Meta.exclude.copy()
        exclude.extend(["location", "include", "invert_species"])
        header_order = ["id"] + BaseSUViewAPISerializer.Meta.header_order.copy()
        header_order.extend(
            [
                "sample_unit_id",
                "sample_time",
                "transect_number",
                "label",
                "depth",
                "relative_depth",
                "transect_len_surveyed",
                "transect_width_name",
                "width_m",
                "observers",
                "data_policy_macroinvertebrate",
                "invert_attribute_id",
                "invert_class",
                "invert_order",
                "invert_family",
                "invert_genus",
                "invert_taxon",
                "size_bin",
                "count",
                "size",
                "density_indha",
                "observation_notes",
                "invert_group_of_interest",
            ]
        )


class BeltInvertMethodObsGeoSerializer(BaseViewAPIGeoSerializer):
    class Meta(BaseViewAPIGeoSerializer.Meta):
        model = BeltInvertObsModel
        exclude = BaseViewAPIGeoSerializer.Meta.exclude.copy()
        exclude.extend(["include", "invert_species"])


class ObsBeltInvertCSVSerializer(ReportSerializer):
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
        ReportField("transect_width_name", "Transect width"),
        ReportField("observers", "Observers", to_names),
        ReportField("invert_class", "Macroinvertebrate class"),
        ReportField("invert_order", "Macroinvertebrate order"),
        ReportField("invert_family", "Macroinvertebrate family"),
        ReportField("invert_genus", "Macroinvertebrate genus"),
        ReportField("invert_taxon", "Macroinvertebrate taxon"),
        ReportField("size_bin", "Size bin"),
        ReportField("size", "Size"),
        ReportField("count", "Count"),
        ReportField("density_indha", "Density ind/ha"),
        ReportField("invert_group_of_interest", "Group of interest"),
        ReportField("observation_notes", "Observation notes"),
        ReportField("site_notes", "Site notes"),
        ReportField("management_notes", "Management notes"),
        ReportField("sample_unit_notes", "Sample unit notes"),
        ReportField("project_notes", "Project notes"),
        ReportField("project_includes_gfcr", "Project includes GFCR", to_yesno),
        ReportField("suggested_citation", "Suggested citation"),
        ReportField("data_policy_macroinvertebrate", "Macroinvertebrate data policy"),
        ReportField("site_id"),
    ]

    additional_fields = [
        ReportField("id"),
        ReportField("project_id"),
        ReportField("country_id"),
        ReportField("management_id"),
        ReportField("sample_event_id"),
        ReportField("sample_unit_id"),
        ReportField("invert_attribute_id"),
    ]


class BeltInvertMethodSUSerializer(BaseSUViewAPISUSerializer):
    class Meta(BaseSUViewAPISUSerializer.Meta):
        model = BeltInvertSUModel
        exclude = BaseSUViewAPISUSerializer.Meta.exclude.copy()
        exclude.extend(["location", "density_indha_group_interest_zeroes"])
        header_order = BaseSUViewAPISUSerializer.Meta.header_order.copy()
        header_order.extend(
            [
                "label",
                "transect_number",
                "transect_len_surveyed",
                "transect_width_name",
                "depth",
                "size_bin",
                "data_policy_macroinvertebrate",
                "total_abundance",
                "density_indha",
                "density_indha_group_interest",
            ]
        )


class BeltInvertMethodSUGeoSerializer(BaseViewAPISUGeoSerializer):
    class Meta(BaseViewAPISUGeoSerializer.Meta):
        model = BeltInvertSUModel
        exclude = BaseViewAPISUGeoSerializer.Meta.exclude.copy()
        exclude.extend(["density_indha_group_interest_zeroes"])


class BeltInvertMethodSUCSVSerializer(ReportSerializer):
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
        ReportField("transect_width_name", "Transect width"),
        ReportField("observers", "Observers", to_names),
        ReportField("size_bin", "Size bin"),
        ReportField("total_abundance", "Total count (ind)"),
        ReportField("density_indha", "Density ind/ha"),
        ReportField("density_indha_group_interest", "Density ind/ha by group of interest"),
        ReportField("site_notes", "Site notes"),
        ReportField("management_notes", "Management notes"),
        ReportField("sample_unit_notes", "Sample unit notes"),
        ReportField("project_notes", "Project notes"),
        ReportField("project_includes_gfcr", "Project includes GFCR", to_yesno),
        ReportField("suggested_citation", "Suggested citation"),
        ReportField("data_policy_macroinvertebrate", "Macroinvertebrate data policy"),
        ReportField("site_id"),
    ]

    additional_fields = [
        ReportField("project_id"),
        ReportField("country_id"),
        ReportField("management_id"),
        ReportField("sample_event_id"),
        ReportField("sample_unit_ids"),
    ]


class BeltInvertMethodSESerializer(BaseSUViewAPISerializer):
    class Meta(BaseSUViewAPISerializer.Meta):
        model = BeltInvertSEModel
        exclude = BaseSUViewAPISerializer.Meta.exclude.copy()
        exclude.append("location")
        header_order = BaseSUViewAPISerializer.Meta.header_order.copy()
        header_order.extend(
            [
                "data_policy_macroinvertebrate",
                "sample_unit_count",
                "depth_avg",
                "depth_sd",
                "count_total_avg",
                "count_total_sd",
                "density_indha_avg",
                "density_indha_sd",
                "density_indha_group_interest_avg",
                "density_indha_group_interest_sd",
            ]
        )


class BeltInvertMethodSEGeoSerializer(BaseViewAPIGeoSerializer):
    class Meta(BaseViewAPIGeoSerializer.Meta):
        model = BeltInvertSEModel


class BeltInvertMethodSECSVSerializer(ReportSerializer):
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
        ReportField("observers", "Observers", to_names),
        ReportField("sample_unit_count", "Sample unit count"),
        ReportField("count_total_avg", "Total count average"),
        ReportField("count_total_sd", "Total count standard deviation"),
        ReportField("density_indha_avg", "Density ind/ha average"),
        ReportField("density_indha_sd", "Density ind/ha standard deviation"),
        ReportField(
            "density_indha_group_interest_avg",
            "Density ind/ha by group of interest average",
        ),
        ReportField(
            "density_indha_group_interest_sd",
            "Density ind/ha by group of interest standard deviation",
        ),
        ReportField("site_notes", "Site notes"),
        ReportField("management_notes", "Management notes"),
        ReportField("project_notes", "Project notes"),
        ReportField("project_includes_gfcr", "Project includes GFCR", to_yesno),
        ReportField("suggested_citation", "Suggested citation"),
        ReportField("data_policy_macroinvertebrate", "Macroinvertebrate data policy"),
        ReportField("site_id"),
    ]

    additional_fields = [
        ReportField("id"),
        ReportField("project_id"),
        ReportField("country_id"),
        ReportField("management_id"),
        ReportField("sample_event_id"),
    ]


class BeltInvertMethodObsFilterSet(BaseSUObsFilterSet):
    transect_len_surveyed = RangeFilter()
    transect_number = RangeFilter()
    count = RangeFilter()
    size = RangeFilter()

    class Meta:
        model = BeltInvertObsModel
        fields = [
            "transect_len_surveyed",
            "transect_number",
            "count",
            "size",
        ]


class BeltInvertMethodObsSQLFilterSet(BeltInvertMethodObsFilterSet):
    class Meta(BeltInvertMethodObsFilterSet.Meta):
        model = BeltInvertObsSQLModel


class BeltInvertMethodSUFilterSet(BaseSUObsFilterSet):
    transect_len_surveyed = RangeFilter()
    transect_number = RangeFilter()
    density_indha = RangeFilter()
    total_abundance = RangeFilter()

    class Meta:
        model = BeltInvertSUModel
        fields = [
            "transect_len_surveyed",
            "transect_number",
            "density_indha",
            "total_abundance",
        ]


class BeltInvertMethodSUSQLFilterSet(BeltInvertMethodSUFilterSet):
    class Meta(BeltInvertMethodSUFilterSet.Meta):
        model = BeltInvertSUSQLModel


class BeltInvertMethodSEFilterSet(BaseSEFilterSet):
    density_indha_avg = RangeFilter()
    count_total_avg = RangeFilter()
    sample_unit_count = RangeFilter()
    depth_avg = RangeFilter()

    class Meta:
        model = BeltInvertSEModel
        fields = [
            "density_indha_avg",
            "count_total_avg",
            "sample_unit_count",
            "depth_avg",
        ]


class BeltInvertMethodSESQLFilterSet(BeltInvertMethodSEFilterSet):
    class Meta(BeltInvertMethodSEFilterSet.Meta):
        model = BeltInvertSESQLModel


class BeltInvertProjectMethodObsView(BaseProjectMethodView):
    drf_label = "beltinvert-obs"
    project_policy = "data_policy_macroinvertebrate"
    model = BeltInvertObsModel
    serializer_class = BeltInvertMethodObsSerializer
    serializer_class_geojson = BeltInvertMethodObsGeoSerializer
    serializer_class_csv = ObsBeltInvertCSVSerializer
    filterset_class = BeltInvertMethodObsFilterSet
    ordering = [
        "site_name",
        "sample_date",
        "transect_number",
        "label",
        "invert_taxon",
        "size",
    ]
    ordering_fields = ordering


class BeltInvertProjectMethodSUView(BaseProjectMethodView):
    drf_label = "beltinvert-su"
    project_policy = "data_policy_macroinvertebrate"
    model = BeltInvertSUModel
    serializer_class = BeltInvertMethodSUSerializer
    serializer_class_geojson = BeltInvertMethodSUGeoSerializer
    serializer_class_csv = BeltInvertMethodSUCSVSerializer
    filterset_class = BeltInvertMethodSUFilterSet
    ordering = ["site_name", "sample_date", "transect_number"]
    ordering_fields = ordering


class BeltInvertProjectMethodSEView(BaseProjectMethodView):
    drf_label = "beltinvert-se"
    project_policy = "data_policy_macroinvertebrate"
    permission_classes = [Or(ProjectDataReadOnlyPermission, ProjectPublicSummaryPermission)]
    model = BeltInvertSEModel
    serializer_class = BeltInvertMethodSESerializer
    serializer_class_geojson = BeltInvertMethodSEGeoSerializer
    serializer_class_csv = BeltInvertMethodSECSVSerializer
    filterset_class = BeltInvertMethodSEFilterSet
    ordering = ["site_name", "sample_date"]
    ordering_fields = ordering
