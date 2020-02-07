from django.conf import settings
from django.db import transaction
from rest_framework import status
from rest_framework.response import Response
from rest_framework.serializers import SerializerMethodField
from rest_framework.decorators import action
from rest_framework_gis.fields import GeometryField
from rest_framework_gis.filterset import GeoFilterSet
from rest_framework_gis.filters import GeometryFilter
from django_filters import DateFromToRangeFilter, BaseInFilter, RangeFilter

from ...models.mermaid import (
    BeltFish,
    BeltTransectWidth,
    ObsBeltFish,
    FishFamily,
    FishGenus,
    FishSpecies,
)
from ..mixins import OrFilterSetMixin
from ...models.view_models import BeltFishObsView, BeltFishSUView, FishAttributeView
from ...utils import calc_biomass_density

from . import *
from ..base import (
    BaseProjectApiViewSet,
    BaseViewAPISerializer,
    BaseViewAPIGeoSerializer,
    BaseTransectFilterSet
)
from ..belt_fish import BeltFishSerializer
from ..fish_belt_transect import FishBeltTransectSerializer
from ..obs_belt_fish import ObsBeltFishSerializer
from ..observer import ObserverSerializer
from ..sample_event import SampleEventSerializer


class BeltFishMethodSerializer(BeltFishSerializer):
    sample_event = SampleEventSerializer(source="transect.sample_event")
    fishbelt_transect = FishBeltTransectSerializer(source="transect")
    observers = ObserverSerializer(many=True)
    obs_belt_fishes = ObsBeltFishSerializer(many=True, source="beltfish_observations")

    class Meta:
        model = BeltFish
        exclude = []


def _get_fish_attribute(row, serializer_instance):
    fish_attribute_id = row.get("fish_attribute")
    if fish_attribute_id is None:
        return None

    lookup = serializer_instance.serializer_cache.get(
        "beltfish_lookups-fish_attributes"
    )
    if lookup:
        return lookup.get(str(fish_attribute_id)) or dict()
    else:
        return FishAttributeView.objects.get(id=fish_attribute_id)


def to_fish_attribute_name(field, row, serializer_instance):
    fa = _get_fish_attribute(row, serializer_instance)
    if fa is None:
        return ""

    elif isinstance(fa, dict):
        return fa.get("name") or ""

    return str(fa)


def _to_fa_attribute(field, row, serializer_instance):
    fa = _get_fish_attribute(row, serializer_instance)
    if fa is None:
        return ""

    elif isinstance(fa, dict):
        return fa.get(field) or ""

    return getattr(fa, field)


def to_fish_attribute_trophic_group(field, row, serializer_instance):
    return _to_fa_attribute("trophic_group", row, serializer_instance)


def to_fish_attribute_trophic_level(field, row, serializer_instance):
    return _to_fa_attribute("trophic_level", row, serializer_instance)


def to_fish_attribute_functional_group(field, row, serializer_instance):
    return _to_fa_attribute("functional_group", row, serializer_instance)


def to_fish_attribute_vulnerability(field, row, serializer_instance):
    return _to_fa_attribute("vulnerability", row, serializer_instance)


def to_constant_a(field, row, serializer_instance):
    return _to_fa_attribute("biomass_constant_a", row, serializer_instance)


def to_constant_b(field, row, serializer_instance):
    return _to_fa_attribute("biomass_constant_b", row, serializer_instance)


def to_constant_c(field, row, serializer_instance):
    return _to_fa_attribute("biomass_constant_c", row, serializer_instance)


def to_transect_width_value(field, row, serializer_instance):
    lookup = serializer_instance.serializer_cache[
        "beltfish_lookups-belt_transect_widths"
    ]
    lookup_val = row.get("beltfish__transect__width_id")
    transect_width = lookup.get(lookup_val)
    if transect_width is None:
        return None
    size = row.get("size")

    condition = transect_width.get_condition(size)
    if condition is None:
        return None

    return condition.val


def to_biomass_kgha(field, row, serializer_instance):
    count = row.get("count")
    size = row.get("size")
    transect_len_surveyed = row.get("beltfish__transect__len_surveyed")
    fa = _get_fish_attribute(row, serializer_instance)
    constant_a = fa.get("biomass_constant_a")
    constant_b = fa.get("biomass_constant_b")
    constant_c = fa.get("biomass_constant_c")
    width_val = to_transect_width_value(field, row, serializer_instance)

    density = calc_biomass_density(
        count,
        size,
        transect_len_surveyed,
        width_val,
        constant_a,
        constant_b,
        constant_c,
    )
    if density is None:
        return ""
    return round(density, 2)


def _get_fish_family(row, serializer_instance):
    fish_family_id = row.get("fish_attribute")
    if fish_family_id is None:
        return None

    lookup = serializer_instance.serializer_cache.get("beltfish_lookups-fish_families")
    if lookup:
        return lookup.get(str(fish_family_id)) or dict()
    else:
        return FishFamily.objects.get(id=fish_family_id)


def to_fish_family_name(field, row, serializer_instance):
    ff = _get_fish_family(row, serializer_instance)

    if ff is None:
        return ""

    elif isinstance(ff, dict):
        return ff.get("name") or ""

    return str(ff)


def _get_fish_genus(row, serializer_instance):
    fish_genus_id = row.get("fish_attribute")
    if fish_genus_id is None:
        return None

    lookup = serializer_instance.serializer_cache.get("beltfish_lookups-fish_genera")
    if lookup:
        return lookup.get(str(fish_genus_id)) or dict()
    else:
        return FishGenus.objects.get(id=fish_genus_id)


def to_fish_genus_name(field, row, serializer_instance):
    fg = _get_fish_genus(row, serializer_instance)

    if fg is None:
        return ""

    elif isinstance(fg, dict):
        return fg.get("name") or ""

    return str(fg)


class ObsBeltFishReportSerializer(
    SampleEventReportSerializer, metaclass=SampleEventReportSerializerMeta
):
    transect_method = "beltfish"
    sample_event_path = "{}__transect__sample_event".format(transect_method)
    idx = 24
    obs_fields = [
        (6, ReportField("beltfish__transect__reef_slope__name", "Reef slope")),
        (idx, ReportField("beltfish__transect__number", "Transect number")),
        (idx + 1, ReportField("beltfish__transect__label", "Transect label")),
        (
            idx + 2,
            ReportField("beltfish__transect__len_surveyed", "Transect length surveyed"),
        ),
        (idx + 3, ReportMethodField("Transect width", to_transect_width_value)),
        (idx + 5, ReportMethodField("Fish family", to_fish_family_name)),
        (idx + 6, ReportMethodField("Fish genus", to_fish_genus_name)),
        (idx + 7, ReportMethodField("Fish taxon", to_fish_attribute_name)),
        (idx + 8, ReportField("beltfish__transect__size_bin__val", "Size bin")),
        (idx + 9, ReportField("size", "Size", to_float)),
        (idx + 10, ReportField("count", "Count")),
        (idx + 11, ReportMethodField("a", to_constant_a)),
        (idx + 12, ReportMethodField("b", to_constant_b)),
        (idx + 13, ReportMethodField("c", to_constant_c)),
        (idx + 14, ReportMethodField("Biomass_kgha", to_biomass_kgha)),
        (idx + 18, ReportMethodField("Trophic group", to_fish_attribute_trophic_group)),
        (idx + 19, ReportMethodField("Trophic level", to_fish_attribute_trophic_level)),
        (
            idx + 20,
            ReportMethodField("Functional group", to_fish_attribute_functional_group),
        ),
        (idx + 21, ReportMethodField("Vulnerability", to_fish_attribute_vulnerability)),
        (idx + 22, ReportField("beltfish__transect__notes", "Observation notes")),
    ]

    non_field_columns = (
        "fish_attribute",
        "beltfish_id",
        "beltfish__transect__sample_event__site__project_id",
        "beltfish__transect__sample_event__management_id",
        "beltfish__transect__width_id",
    )

    def preserialize(self, queryset=None):
        super(ObsBeltFishReportSerializer, self).preserialize(queryset=queryset)

        # Fish Attributes
        fish_attributes = FishAttributeView.objects.all()
        fish_families = FishFamily.objects.all()
        fish_genera = FishGenus.objects.select_related("family").all()
        fish_species = FishSpecies.objects.select_related(
            "genus", "genus__family"
        ).all()

        # Fish Family Lookup
        fish_family_lookup = {str(ff.id): dict(name=ff.name) for ff in fish_families}
        fish_family_lookup.update(
            {str(fg.id): dict(name=fg.family.name) for fg in fish_genera}
        )
        fish_family_lookup.update(
            {str(fs.id): dict(name=fs.genus.family.name) for fs in fish_species}
        )

        # Fish Genus Lookup
        fish_genus_lookup = {str(fg.id): dict(name=fg.name) for fg in fish_genera}
        fish_genus_lookup.update(
            {str(fs.id): dict(name=fs.genus.name) for fs in fish_species}
        )

        # Fish Attribute Lookup
        fish_attribute_lookup = {
            str(fa.id): dict(
                name=fa.name,
                biomass_constant_a=fa.biomass_constant_a,
                biomass_constant_b=fa.biomass_constant_b,
                biomass_constant_c=fa.biomass_constant_c,
                trophic_group=fa.trophic_group,
                trophic_level=fa.trophic_level,
                functional_group=fa.functional_group,
                vulnerability=fa.vulnerability,
            )
            for fa in fish_attributes
        }

        if len(fish_family_lookup.keys()) > 0:
            self.serializer_cache["beltfish_lookups-fish_families"] = fish_family_lookup

        if len(fish_genus_lookup.keys()) > 0:
            self.serializer_cache["beltfish_lookups-fish_genera"] = fish_genus_lookup

        if len(fish_attribute_lookup.keys()) > 0:
            self.serializer_cache[
                "beltfish_lookups-fish_attributes"
            ] = fish_attribute_lookup

        widths = BeltTransectWidth.objects.prefetch_related("conditions").all()
        self.serializer_cache["beltfish_lookups-belt_transect_widths"] = {
            btw.id: btw for btw in widths
        }


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
        return fieldreport(
            self,
            request,
            *args,
            model_cls=ObsBeltFish,
            serializer_class=ObsBeltFishReportSerializer,
            fk="beltfish",
            order_by=(
                "Site",
                "Transect number",
                "Transect label",
                "Fish family",
                "Fish genus",
                "Fish taxon",
                "Size",
            ),
            **kwargs
        )

    # @action(detail=False, methods=["get"], serializer_class=BeltFishMethodObsSerializer)
    # def obstransectbeltfishes(self, request, *args, **kwargs):
    #     # obs = BeltFishObsView.objects.filter(project_id="9de82789-c38e-462e-a1a8-e02c020c7a35")
    #     qs = BeltFishObsView.objects.filter(project_id="2c56b92b-ba1c-491f-8b62-23b1dc728890")
    #     # self.limit_to_project(request, *args, **kwargs)
    #     # page = self.paginate_queryset(recent_users)
    #     # if page is not None:
    #     #     serializer = self.get_serializer(page, many=True)
    #     #     return self.get_paginated_response(serializer.data)
    #
    #     serializer = self.get_serializer(qs, many=True)
    #     print(serializer)
    #     return Response(serializer.data)


class BeltFishMethodObsSerializer(BaseViewAPISerializer):

    class Meta:
        model = BeltFishObsView
        exclude = ["location"]  # TODO


class BeltFishMethodObsCSVSerializer(BeltFishMethodObsSerializer):
    observers = SerializerMethodField()


class BeltFishMethodObsGeoSerializer(BaseViewAPIGeoSerializer):

    class Meta:
        model = BeltFishObsView
        exclude = []  # TODO
        geo_field = "location"


class BeltFishMethodSUSerializer(BaseViewAPISerializer):

    class Meta:
        model = BeltFishSUView
        exclude = ["location"]  # TODO


class BeltFishMethodSUCSVSerializer(BeltFishMethodSUSerializer):
    observers = SerializerMethodField()


class BeltFishMethodSUGeoSerializer(BaseViewAPIGeoSerializer):

    class Meta:
        model = BeltFishSUView
        exclude = []  # TODO
        geo_field = "location"


class BeltFishMethodObsFilterSet(BaseTransectFilterSet):
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
    biomass_kgha = RangeFilter()

    class Meta:
        model = BeltFishSUView
        fields = [
            "size_bin",
            "biomass_kgha",
            "data_policy_beltfish",
        ]


class BeltFishMethodObsView(BaseMethodView):
    drf_label = "beltfish"
    project_policy = "data_policy_beltfish"
    serializer_class = BeltFishMethodObsSerializer
    serializer_class_geojson = BeltFishMethodObsGeoSerializer
    serializer_class_csv = BeltFishMethodObsCSVSerializer
    filterset_class = BeltFishMethodObsFilterSet
    queryset = BeltFishObsView.objects.all()  # TODO: order_by, select_related


class BeltFishMethodSUView(BaseMethodView):
    drf_label = "beltfish"
    project_policy = "data_policy_beltfish"
    serializer_class = BeltFishMethodSUSerializer
    serializer_class_geojson = BeltFishMethodSUGeoSerializer
    serializer_class_csv = BeltFishMethodSUCSVSerializer
    filterset_class = BeltFishMethodSUFilterSet
    queryset = BeltFishSUView.objects.all()  # TODO: order_by, select_related
