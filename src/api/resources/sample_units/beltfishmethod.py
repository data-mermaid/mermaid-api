from django.db import transaction
from django.db.models import Q
from django_filters import BaseInFilter, RangeFilter
from rest_framework.decorators import action
from rest_condition import Or
from rest_framework import status
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError

from ...models import FISHBELT_PROTOCOL, BeltFishObsSQLModel, BeltFishSESQLModel, BeltFishSUSQLModel
from ...models import AuditRecord, BeltFish, CollectRecord, Project
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
from ..belt_fish import BeltFishSerializer
from ..collect_record import CollectRecordSerializer
from ..fish_belt_transect import FishBeltTransectSerializer
from ..obs_belt_fish import ObsBeltFishSerializer
from ..observer import ObserverSerializer
from ..sample_event import SampleEventSerializer
from ...utils.sample_unit_methods import edit_transect_method
from . import (
    BaseProjectMethodView,
    clean_sample_event_models,
    save_model,
    save_one_to_many
)


class ObsBeltFishCSVSerializer(ReportSerializer):
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
        ReportField("transect_width_name", "Transect width"),
        ReportField("observers", "Observers", to_names),
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
        ReportField("functional_group", "Functional group"),
        ReportField("vulnerability", "Vulnerability"),
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
        ReportField("site_id"),
        ReportField("project_id"),
        ReportField("project_notes"),
        ReportField("contact_link"),
        ReportField("tags"),
        ReportField("country_id"),
        ReportField("management_id"),
        ReportField("sample_event_id"),
        ReportField("sample_unit_id"),
        ReportField("data_policy_beltfish"),
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

            clean_sample_event_models(nested_data["sample_event"])

            transaction.savepoint_commit(sid)

            belt_fish = BeltFish.objects.get(id=belt_fish_id)
            return Response(
                BeltFishMethodSerializer(belt_fish).data, status=status.HTTP_200_OK
            )

        except:
            transaction.savepoint_rollback(sid)
            raise
    

    @transaction.atomic
    @action(
        detail=True, methods=["PUT"] #, permission_classes=[ProjectDataAdminPermission]
    )
    def edit(self, request, project_pk, pk):
        collect_record_owner = Project.objects.get_or_none(id=request.data.get("owner"))
        if collect_record_owner is None:
            collect_record_owner = request.user.profile

        try:
            collect_record = edit_transect_method(
                self.serializer_class,
                collect_record_owner,
                request,
                pk,
                FISHBELT_PROTOCOL
            )
            return Response({"id": str(collect_record.pk)})
        except Exception as err:
            return Response(str(err), status=500)
      

class BeltFishMethodObsSerializer(BaseSUViewAPISerializer):
    class Meta(BaseSUViewAPISerializer.Meta):
        model = BeltFishObsSQLModel
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
                "relative_depth",
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


class BeltFishMethodObsGeoSerializer(BaseViewAPIGeoSerializer):
    class Meta(BaseViewAPIGeoSerializer.Meta):
        model = BeltFishObsSQLModel


class BeltFishMethodSUSerializer(BaseSUViewAPISerializer):
    class Meta(BaseSUViewAPISerializer.Meta):
        model = BeltFishSUSQLModel
        exclude = BaseSUViewAPISerializer.Meta.exclude.copy()
        exclude.append("location")
        header_order = BaseSUViewAPISerializer.Meta.header_order.copy()
        header_order.extend(
            [
                "label",
                "transect_number",
                "transect_len_surveyed",
                "transect_width_name",
                "depth",
                "reef_slope",
                "size_bin",
                "data_policy_beltfish",
                "total_abundance",
                "biomass_kgha",
                "biomass_kgha_by_trophic_group",
                "biomass_kgha_by_fish_family",
            ]
        )


class BeltFishMethodSUCSVSerializer(ReportSerializer):
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
        ReportField("transect_width_name", "Transect width"),
        ReportField("observers", "Observers", to_names),
        ReportField("size_bin", "Size bin"),
        ReportField("total_abundance", "Total abundance"),
        ReportField("biomass_kgha", "Biomass_kgha"),
        ReportField("biomass_kgha_by_trophic_group", "Biomass kgha by trophic group"),
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
        ReportField("data_policy_beltfish"),
    ]


class BeltFishMethodSECSVSerializer(ReportSerializer):
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
        ReportField("biomass_kgha_avg", "Biomass_kgha average"),
        ReportField("biomass_kgha_by_trophic_group_avg", "Biomass kgha by trophic group average"),
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
        ReportField("data_policy_beltfish"),
    ]


class BeltFishMethodSUGeoSerializer(BaseViewAPIGeoSerializer):
    class Meta(BaseViewAPIGeoSerializer.Meta):
        model = BeltFishSUSQLModel


class BeltFishMethodSESerializer(BaseSUViewAPISerializer):
    class Meta(BaseSUViewAPISerializer.Meta):
        model = BeltFishSESQLModel
        exclude = BaseSUViewAPISerializer.Meta.exclude.copy()
        exclude.append("location")
        header_order = BaseSUViewAPISerializer.Meta.header_order.copy()
        header_order.extend(
            [
                "data_policy_beltfish",
                "sample_unit_count",
                "depth_avg",
                "biomass_kgha_avg",
                "biomass_kgha_by_trophic_group_avg",
                "biomass_kgha_by_fish_family_avg",
            ]
        )


class BeltFishMethodSEGeoSerializer(BaseViewAPIGeoSerializer):
    class Meta(BaseViewAPIGeoSerializer.Meta):
        model = BeltFishSESQLModel


class BeltFishMethodObsFilterSet(BaseSUObsFilterSet):
    transect_len_surveyed = RangeFilter()
    reef_slope = BaseInFilter(method="char_lookup")
    fish_family = BaseInFilter(method="char_lookup")
    fish_genus = BaseInFilter(method="char_lookup")
    fish_taxon = BaseInFilter(method="char_lookup")
    trophic_group = BaseInFilter(method="char_lookup")
    trophic_level = RangeFilter()
    functional_group = BaseInFilter(method="id_lookup")
    vulnerability = RangeFilter()
    size = RangeFilter()
    count = RangeFilter()
    biomass_kgha = RangeFilter()

    class Meta:
        model = BeltFishObsSQLModel
        fields = [
            "transect_len_surveyed",
            "reef_slope",
            "transect_number",
            "fish_taxon",
            "fish_family",
            "fish_genus",
            "trophic_group",
            "trophic_level",
            "functional_group",
            "vulnerability",
            "size",
            "count",
            "biomass_kgha",
        ]


class BeltFishMethodSUFilterSet(BaseSUObsFilterSet):
    transect_len_surveyed = RangeFilter()
    reef_slope = BaseInFilter(method="char_lookup")
    biomass_kgha = RangeFilter()

    class Meta:
        model = BeltFishSUSQLModel
        fields = [
            "transect_len_surveyed",
            "reef_slope",
            "transect_number",
            "biomass_kgha",
        ]


class BeltFishMethodSEFilterSet(BaseSEFilterSet):
    biomass_kgha_avg = RangeFilter()
    sample_unit_count = RangeFilter()
    depth_avg = RangeFilter()

    class Meta:
        model = BeltFishSESQLModel
        fields = [
            "biomass_kgha_avg",
            "sample_unit_count",
            "depth_avg",
        ]


class BeltFishProjectMethodObsView(BaseProjectMethodView):
    drf_label = "beltfish-obs"
    project_policy = "data_policy_beltfish"
    serializer_class = BeltFishMethodObsSerializer
    serializer_class_geojson = BeltFishMethodObsGeoSerializer
    serializer_class_csv = ObsBeltFishCSVSerializer
    filterset_class = BeltFishMethodObsFilterSet
    order_by = (
        "site_name",
        "sample_date",
        "transect_number",
        "label",
        "fish_family",
        "fish_genus",
        "fish_taxon",
        "size",
    )

    model = BeltFishObsSQLModel

    def get_queryset(self):
        project_id = self.kwargs.get("project_pk")
        return self.model.objects.all().sql_table(
            project_id=project_id
        ).filter(
            Q(size__isnull=False)
            | Q(count__isnull=False)
            | Q(biomass_kgha__isnull=False)
        )


class BeltFishProjectMethodSUView(BaseProjectMethodView):
    drf_label = "beltfish-su"
    project_policy = "data_policy_beltfish"
    serializer_class = BeltFishMethodSUSerializer
    serializer_class_geojson = BeltFishMethodSUGeoSerializer
    serializer_class_csv = BeltFishMethodSUCSVSerializer
    filterset_class = BeltFishMethodSUFilterSet
    model = BeltFishSUSQLModel
    order_by = (
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
    serializer_class_csv = BeltFishMethodSECSVSerializer
    filterset_class = BeltFishMethodSEFilterSet
    model = BeltFishSESQLModel
    order_by = (
        "site_name", "sample_date"
    )
