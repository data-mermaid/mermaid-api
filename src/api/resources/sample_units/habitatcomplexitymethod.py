from django.db import transaction
from rest_framework import status
from rest_framework.response import Response
from rest_framework.serializers import SerializerMethodField
from django_filters import BaseInFilter, RangeFilter

from .. import fieldreport
from ...models.mermaid import HabitatComplexity, ObsHabitatComplexity
from ...models.view_models import (
    HabitatComplexityObsView,
    HabitatComplexitySUView,
    HabitatComplexitySEView,
)

from . import *
from ..base import (
    BaseProjectApiViewSet,
    BaseViewAPISerializer,
    BaseViewAPIGeoSerializer,
    BaseTransectFilterSet,
)
from ..habitat_complexity import HabitatComplexitySerializer
from ..benthic_transect import BenthicTransectSerializer
from ..obs_habitat_complexity import ObsHabitatComplexitySerializer
from ..observer import ObserverSerializer
from ..sample_event import SampleEventSerializer


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


class ObsHabitatComplexityReportSerializer(
    SampleEventReportSerializer, metaclass=SampleEventReportSerializerMeta
):
    transect_method = "habitatcomplexity"
    sample_event_path = "{}__transect__sample_event".format(transect_method)

    idx = 24
    obs_fields = [
        (6, ReportField("habitatcomplexity__transect__reef_slope__name", "Reef slope")),
        (idx, ReportField("habitatcomplexity__transect__number", "Transect number")),
        (idx + 1, ReportField("habitatcomplexity__transect__label", "Transect label")),
        (
            idx + 2,
            ReportField(
                "habitatcomplexity__transect__len_surveyed", "Transect length surveyed"
            ),
        ),
        (idx + 4, ReportField("interval", "Interval (m)")),
        (idx + 5, ReportField("score__val", "Habitat complexity value")),
        (idx + 6, ReportField("score__name", "Habitat complexity name")),
        (
            idx + 10,
            ReportField("habitatcomplexity__transect__notes", "Observation notes"),
        ),
    ]

    non_field_columns = (
        "habitatcomplexity_id",
        "habitatcomplexity__transect__sample_event__site__project_id",
        "habitatcomplexity__transect__sample_event__management_id",
    )

    class Meta:
        model = HabitatComplexity


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

    @action(detail=False, methods=["get"])
    def fieldreport(self, request, *args, **kwargs):
        return fieldreport(
            self,
            request,
            *args,
            model_cls=ObsHabitatComplexity,
            serializer_class=ObsHabitatComplexityReportSerializer,
            fk="habitatcomplexity",
            order_by=("Site", "Transect number", "Transect label"),
            **kwargs
        )


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


class HabitatComplexityMethodObsCSVSerializer(HabitatComplexityMethodObsSerializer):
    observers = SerializerMethodField()


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
    serializer_class_csv = HabitatComplexityMethodObsCSVSerializer
    filterset_class = HabitatComplexityMethodObsFilterSet
    queryset = HabitatComplexityObsView.objects.exclude(
        project_status=Project.TEST
    ).order_by("site_name", "sample_date", "transect_number", "label", "interval")


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
