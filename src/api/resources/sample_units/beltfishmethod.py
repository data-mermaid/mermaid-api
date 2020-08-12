from django.db import transaction
from django.db.models import Q
from django_filters import BaseInFilter, RangeFilter
from rest_framework import status
from rest_framework.response import Response
from rest_framework.serializers import SerializerMethodField

from ...models.mermaid import BeltFish
from ...models.view_models import BeltFishObsView, BeltFishSEView, BeltFishSUView
from ...reports import field_reports
from ...reports.fields import ReportField
from ...reports.formatters import (
    handle_none,
    to_day,
    to_latitude,
    to_longitude,
    to_month,
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
from ..belt_fish import BeltFishSerializer
from ..fish_belt_transect import FishBeltTransectSerializer
from ..obs_belt_fish import ObsBeltFishSerializer
from ..observer import ObserverSerializer
from ..sample_event import SampleEventSerializer
from . import *


@handle_none()
def to_governance(value, field, row, serializer_instance):
    vals = []
    for v in value:
        vals.extend(v.split("/"))

    return ",".join(vals)


@handle_none()
def to_observers(value, field, row, serializer_instance):
    vals = [v["name"] for v in value]
    return ",".join(vals)


class ObservationsFieldReportSerializer(ReportSerializer):
    sample_unit_method = ""
    observation_fields = []
    non_field_columns = []


class ObsBeltFishFieldReportSerializer(ObservationsFieldReportSerializer):
    fields = [
        ReportField("project_name", "Project name"),
        ReportField("country_name", "Country"),
        ReportField("site_name", "Site"),
        ReportField("location", "Latitude", to_latitude),
        ReportField("location", "Longitude", to_longitude,),
        ReportField("reef_exposure", "Exposure"),
        ReportField("reef_slope", "Reef slope"),
        ReportField("reef_type", "Reef type"),
        ReportField("reef_zone", "Reef zone"),
        ReportField("sample_date", "Year", to_year),
        ReportField("sample_date", "Month", to_month),
        ReportField("sample_date", "Day", to_day),
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
        ReportField("transect_width_name", "Transect width"),
        ReportField("observers", "Observer", to_observers),
        ReportField("fish_family", "Fish family"),
        ReportField("fish_genus", "Fish genus"),
        ReportField("fish_taxon", "Fish taxon"),
        ReportField("size_bin", "Size bin"),
        ReportField("size", "Size"),
        ReportField("count", "Count"),
        ReportField("biomass_constant_a", "a"),
        ReportField("biomass_constant_b", "b"),
        ReportField("biomass_constant_c", "c"),
        ReportField("biomass_kgha", "Biomass_kgha"),
        ReportField("site_notes", "Site notes"),
        ReportField("sample_event_notes", "Sampling event notes"),
        ReportField("management_notes", "Management notes"),
        ReportField("trophic_group", "Trophic group"),
        ReportField("trophic_level", "Trophic level"),
        ReportField("trophic_group", "Functional group"),
        ReportField("vulnerability", "Vulnerability"),
        ReportField("observation_notes", "Observation notes"),
    ]


class BeltFishMethodSerializer(BeltFishSerializer):
    sample_event = SampleEventSerializer(source="transect.sample_event")
    fishbelt_transect = FishBeltTransectSerializer(source="transect")
    observers = ObserverSerializer(many=True)
    obs_belt_fishes = ObsBeltFishSerializer(many=True, source="beltfish_observations")

    class Meta:
        model = BeltFish
        exclude = []


class BeltFishMethodView(BaseProjectApiViewSet):
    project_policy = "data_policy_beltfish"
    queryset = (
        BeltFish.objects.select_related("transect", "transect__sample_event")
        .all()
        .order_by("updated_on", "id")
    )
    serializer_class = BeltFishMethodSerializer
    http_method_names = ["get", "put", "head", "delete"]

    @transaction.atomic
    def update(self, request, project_pk, pk=None):
        errors = {}
        is_valid = True
        nested_data = dict(
            sample_event=request.data.get("sample_event"),
            fishbelt_transect=request.data.get("fishbelt_transect"),
            observers=request.data.get("observers"),
            obs_belt_fishes=request.data.get("obs_belt_fishes"),
        )
        belt_fish_data = {k: v for k, v in request.data.items() if k not in nested_data}
        belt_fish_id = belt_fish_data["id"]

        context = dict(request=request)

        # Save models in a transaction
        sid = transaction.savepoint()
        try:
            belt_fish = BeltFish.objects.get(id=belt_fish_id)

            # Observers
            check, errs = save_one_to_many(
                foreign_key=("transectmethod", belt_fish_id),
                database_records=belt_fish.observers.all(),
                data=request.data.get("observers") or [],
                serializer_class=ObserverSerializer,
                context=context,
            )
            if check is False:
                is_valid = False
                errors["observers"] = errs

            # Observations
            check, errs = save_one_to_many(
                foreign_key=("beltfish", belt_fish_id),
                database_records=belt_fish.beltfish_observations.all(),
                data=request.data.get("obs_belt_fishes") or [],
                serializer_class=ObsBeltFishSerializer,
                context=context,
            )
            if check is False:
                is_valid = False
                errors["obs_belt_fishes"] = errs

            # Sample Event
            check, errs = save_model(
                data=nested_data["sample_event"],
                serializer_class=SampleEventSerializer,
                context=context,
            )
            if check is False:
                is_valid = False
                errors["sample_event"] = errs

            # Fishbelt Transect
            check, errs = save_model(
                data=nested_data["fishbelt_transect"],
                serializer_class=FishBeltTransectSerializer,
                context=context,
            )
            if check is False:
                is_valid = False
                errors["fishbelt_transect"] = errs

            # Belt Fish
            check, errs = save_model(
                data=belt_fish_data,
                serializer_class=BeltFishSerializer,
                context=context,
            )
            if check is False:
                is_valid = False
                errors["belt_fish"] = errs

            if is_valid is False:
                transaction.savepoint_rollback(sid)
                return Response(data=errors, status=status.HTTP_400_BAD_REQUEST)

            transaction.savepoint_commit(sid)

            belt_fish = BeltFish.objects.get(id=belt_fish_id)
            return Response(
                BeltFishMethodSerializer(belt_fish).data, status=status.HTTP_200_OK
            )

        except:
            transaction.savepoint_rollback(sid)
            raise

    @action(
        detail=False,
        methods=["get"],
        permission_classes=[Or(ProjectDataReadOnlyPermission, ProjectPublicPermission)],
    )
    def fieldreport(self, request, *args, **kwargs):
        return field_reports.get_csv_response(
            project_api_viewset=self,
            serializer_class=ObsBeltFishFieldReportSerializer,
            report_model_cls=BeltFishObsView,
            project_pk=kwargs["project_pk"],
            relationship=("id" ", sample_unit_id",),
            order_by=(
                "Site",
                "Transect number",
                "Transect label",
                "Fish family",
                "Fish genus",
                "Fish taxon",
                "Size",
            ),
            file_name_prefix="beltfish",
        )


class BeltFishMethodObsSerializer(BaseViewAPISerializer):
    class Meta(BaseViewAPISerializer.Meta):
        model = BeltFishObsView
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
                "transect_width_name",
                "reef_slope",
                "size_bin",
                "observers",
                "data_policy_beltfish",
                "fish_family",
                "fish_genus",
                "fish_taxon",
                "trophic_group",
                "trophic_level",
                "functional_group",
                "vulnerability",
                "biomass_constant_a",
                "biomass_constant_b",
                "biomass_constant_c",
                "size",
                "count",
                "biomass_kgha",
                "observation_notes",
            ]
        )


class BeltFishMethodObsCSVSerializer(BeltFishMethodObsSerializer):
    observers = SerializerMethodField()


class BeltFishMethodObsGeoSerializer(BaseViewAPIGeoSerializer):
    class Meta(BaseViewAPIGeoSerializer.Meta):
        model = BeltFishObsView


class BeltFishMethodSUSerializer(BaseViewAPISerializer):
    class Meta(BaseViewAPISerializer.Meta):
        model = BeltFishSUView
        exclude = BaseViewAPISerializer.Meta.exclude.copy()
        exclude.append("location")
        header_order = BaseViewAPISerializer.Meta.header_order.copy()
        header_order.extend(
            [
                "transect_number",
                "transect_len_surveyed",
                "transect_width_name",
                "depth",
                "reef_slope",
                "size_bin",
                "data_policy_beltfish",
                "biomass_kgha",
                "biomass_kgha_by_trophic_group",
            ]
        )


class BeltFishMethodSUCSVSerializer(BeltFishMethodSUSerializer):
    observers = SerializerMethodField()


class BeltFishMethodSUGeoSerializer(BaseViewAPIGeoSerializer):
    class Meta(BaseViewAPIGeoSerializer.Meta):
        model = BeltFishSUView


class BeltFishMethodSESerializer(BaseViewAPISerializer):
    class Meta(BaseViewAPISerializer.Meta):
        model = BeltFishSEView
        exclude = BaseViewAPISerializer.Meta.exclude.copy()
        exclude.append("location")
        header_order = BaseViewAPISerializer.Meta.header_order.copy()
        header_order.extend(
            [
                "data_policy_beltfish",
                "sample_unit_count",
                "depth_avg",
                "biomass_kgha_avg",
                "biomass_kgha_by_trophic_group_avg",
            ]
        )


class BeltFishMethodSEGeoSerializer(BaseViewAPIGeoSerializer):
    class Meta(BaseViewAPIGeoSerializer.Meta):
        model = BeltFishSEView


class BeltFishMethodObsFilterSet(BaseTransectFilterSet):
    depth = RangeFilter()
    sample_unit_id = BaseInFilter(method="id_lookup")
    observers = BaseInFilter(method="json_name_lookup")
    transect_len_surveyed = RangeFilter()
    reef_slope = BaseInFilter(method="char_lookup")
    fish_family = BaseInFilter(method="id_lookup")
    fish_genus = BaseInFilter(method="id_lookup")
    fish_taxon = BaseInFilter(method="id_lookup")
    trophic_group = BaseInFilter(method="id_lookup")
    trophic_level = RangeFilter()
    functional_group = BaseInFilter(method="id_lookup")
    vulnerability = RangeFilter()
    size = RangeFilter()
    count = RangeFilter()
    biomass_kgha = RangeFilter()

    class Meta:
        model = BeltFishObsView
        fields = [
            "depth",
            "sample_unit_id",
            "observers",
            "transect_len_surveyed",
            "reef_slope",
            "transect_number",
            "label",
            "fish_taxon",
            "fish_family",
            "fish_genus",
            "trophic_group",
            "trophic_level",
            "functional_group",
            "vulnerability",
            "size",
            "count",
            "size_bin",
            "biomass_kgha",
            "data_policy_beltfish",
        ]


class BeltFishMethodSUFilterSet(BaseTransectFilterSet):
    transect_len_surveyed = RangeFilter()
    depth = RangeFilter()
    observers = BaseInFilter(method="json_name_lookup")
    reef_slope = BaseInFilter(method="char_lookup")
    biomass_kgha = RangeFilter()

    class Meta:
        model = BeltFishSUView
        fields = [
            "depth",
            "observers",
            "transect_len_surveyed",
            "reef_slope",
            "transect_number",
            "size_bin",
            "biomass_kgha",
            "data_policy_beltfish",
        ]


class BeltFishMethodSEFilterSet(BaseTransectFilterSet):
    biomass_kgha_avg = RangeFilter()
    sample_unit_count = RangeFilter()
    depth_avg = RangeFilter()

    class Meta:
        model = BeltFishSEView
        fields = [
            "biomass_kgha_avg",
            "sample_unit_count",
            "depth_avg",
            "data_policy_beltfish",
        ]


class BeltFishProjectMethodObsView(BaseProjectMethodView):
    drf_label = "beltfish-obs"
    project_policy = "data_policy_beltfish"
    serializer_class = BeltFishMethodObsSerializer
    serializer_class_geojson = BeltFishMethodObsGeoSerializer
    serializer_class_csv = BeltFishMethodObsCSVSerializer
    filterset_class = BeltFishMethodObsFilterSet
    queryset = BeltFishObsView.objects.exclude(
        Q(project_status=Project.TEST)
        | Q(size__isnull=True)
        | Q(count__isnull=True)
        | Q(biomass_kgha__isnull=True)
    ).order_by(
        "site_name",
        "sample_date",
        "transect_number",
        "label",
        "fish_family",
        "fish_genus",
        "fish_taxon",
        "size",
    )


class BeltFishProjectMethodSUView(BaseProjectMethodView):
    drf_label = "beltfish-su"
    project_policy = "data_policy_beltfish"
    serializer_class = BeltFishMethodSUSerializer
    serializer_class_geojson = BeltFishMethodSUGeoSerializer
    serializer_class_csv = BeltFishMethodSUCSVSerializer
    filterset_class = BeltFishMethodSUFilterSet
    queryset = BeltFishSUView.objects.exclude(project_status=Project.TEST).order_by(
        "site_name", "sample_date", "transect_number"
    )


class BeltFishProjectMethodSEView(BaseProjectMethodView):
    drf_label = "beltfish-se"
    project_policy = "data_policy_beltfish"
    permission_classes = [
        Or(ProjectDataReadOnlyPermission, ProjectPublicSummaryPermission)
    ]
    serializer_class = BeltFishMethodSESerializer
    serializer_class_geojson = BeltFishMethodSEGeoSerializer
    serializer_class_csv = BeltFishMethodSESerializer
    filterset_class = BeltFishMethodSEFilterSet
    queryset = BeltFishSEView.objects.exclude(project_status=Project.TEST).order_by(
        "site_name", "sample_date"
    )
