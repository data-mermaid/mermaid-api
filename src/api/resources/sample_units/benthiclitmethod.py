from django.db import transaction
from django.db.models import Sum
from django_filters import BaseInFilter, RangeFilter
from rest_condition import Or
from rest_framework import status
from rest_framework.response import Response
from rest_framework.serializers import SerializerMethodField

# from .. import fieldreport
from ...models.mermaid import BenthicAttribute, BenthicLIT, ObsBenthicLIT, Project
from ...models.view_models import BenthicLITObsView, BenthicLITSEView, BenthicLITSUView
from ...permissions import ProjectDataReadOnlyPermission, ProjectPublicSummaryPermission
from ...reports.fields import ReportField
from ...reports.formatters import (
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
from ..benthic_lit import BenthicLITSerializer
from ..benthic_transect import BenthicTransectSerializer
from ..obs_benthic_lit import ObsBenthicLITSerializer
from ..observer import ObserverSerializer
from ..sample_event import SampleEventSerializer
from . import BaseProjectMethodView, save_model, save_one_to_many


class BenthicLITMethodSerializer(BenthicLITSerializer):
    sample_event = SampleEventSerializer(source="transect.sample_event")
    benthic_transect = BenthicTransectSerializer(source="transect")
    observers = ObserverSerializer(many=True)
    obs_benthic_lits = ObsBenthicLITSerializer(many=True, source="obsbenthiclit_set")

    class Meta:
        model = BenthicLIT
        exclude = []


class BenthicLITMethodView(BaseProjectApiViewSet):
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
        benthic_lit_data = {
            k: v for k, v in request.data.items() if k not in nested_data
        }
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

            transaction.savepoint_commit(sid)

            benthic_lit = BenthicLIT.objects.get(id=benthic_lit_id)
            return Response(
                BenthicLITMethodSerializer(benthic_lit).data, status=status.HTTP_200_OK
            )

        except:
            transaction.savepoint_rollback(sid)
            raise


class BenthicLITMethodObsSerializer(BaseSUViewAPISerializer):
    class Meta(BaseSUViewAPISerializer.Meta):
        model = BenthicLITObsView
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
                "data_policy_benthiclit",
                "length",
                "benthic_category",
                "benthic_attribute",
                "growth_form",
                "observation_notes",
            ]
        )


class ObsBenthicLITCSVSerializer(ReportSerializer):
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
        ReportField("observers", "Observers", to_names),
        ReportField("benthic_category", "Benthic category"),
        ReportField("benthic_attribute", "Benthic attribute"),
        ReportField("growth_form", "Growth form"),
        ReportField("length", "LIT (cm)"),
        ReportField("total_length", "Total transect cm"),
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
        ReportField("data_policy_benthiclit"),
    ]


class BenthicLITMethodObsGeoSerializer(BaseViewAPIGeoSerializer):
    class Meta(BaseViewAPIGeoSerializer.Meta):
        model = BenthicLITObsView


class BenthicLITMethodSUSerializer(BaseSUViewAPISerializer):
    class Meta(BaseSUViewAPISerializer.Meta):
        model = BenthicLITSUView
        exclude = BaseSUViewAPISerializer.Meta.exclude.copy()
        exclude.append("location")
        header_order = BaseSUViewAPISerializer.Meta.header_order.copy()
        header_order.extend(
            [
                "transect_number",
                "transect_len_surveyed",
                "depth",
                "reef_slope",
                "percent_cover_by_benthic_category",
                "data_policy_benthiclit",
            ]
        )


class BenthicLITMethodSUCSVSerializer(BenthicLITMethodSUSerializer):
    observers = SerializerMethodField()


class BenthicLITMethodSUGeoSerializer(BaseViewAPIGeoSerializer):
    class Meta(BaseViewAPIGeoSerializer.Meta):
        model = BenthicLITSUView


class BenthicLITMethodSESerializer(BaseSUViewAPISerializer):
    class Meta(BaseSUViewAPISerializer.Meta):
        model = BenthicLITSEView
        exclude = BaseSUViewAPISerializer.Meta.exclude.copy()
        exclude.append("location")
        header_order = BaseSUViewAPISerializer.Meta.header_order.copy()
        header_order.extend(
            [
                "data_policy_benthiclit",
                "sample_unit_count",
                "depth_avg",
                "percent_cover_by_benthic_category_avg",
            ]
        )


class BenthicLITMethodSEGeoSerializer(BaseViewAPIGeoSerializer):
    class Meta(BaseViewAPIGeoSerializer.Meta):
        model = BenthicLITSEView


class BenthicLITMethodObsFilterSet(BaseSUObsFilterSet):
    transect_len_surveyed = RangeFilter()
    reef_slope = BaseInFilter(method="char_lookup")
    length = RangeFilter()

    class Meta:
        model = BenthicLITObsView
        fields = [
            "transect_len_surveyed",
            "reef_slope",
            "transect_number",
            "length",
            "benthic_category",
            "benthic_attribute",
            "growth_form",
            "data_policy_benthiclit",
        ]


class BenthicLITMethodSUFilterSet(BaseSUObsFilterSet):
    transect_len_surveyed = RangeFilter()
    reef_slope = BaseInFilter(method="char_lookup")

    class Meta:
        model = BenthicLITSUView
        fields = [
            "transect_len_surveyed",
            "reef_slope",
            "transect_number",
            "data_policy_benthiclit",
        ]


class BenthicLITMethodSEFilterSet(BaseSEFilterSet):
    sample_unit_count = RangeFilter()
    depth_avg = RangeFilter()

    class Meta:
        model = BenthicLITSEView
        fields = ["sample_unit_count", "depth_avg", "data_policy_benthiclit"]


class BenthicLITProjectMethodObsView(BaseProjectMethodView):
    drf_label = "benthiclit-obs"
    project_policy = "data_policy_benthiclit"
    serializer_class = BenthicLITMethodObsSerializer
    serializer_class_geojson = BenthicLITMethodObsGeoSerializer
    serializer_class_csv = ObsBenthicLITCSVSerializer
    filterset_class = BenthicLITMethodObsFilterSet
    queryset = BenthicLITObsView.objects.filter(
        # project_status=Project.TEST
    )

    order_by = ("site_name", "sample_date", "transect_number", "label")


class BenthicLITProjectMethodSUView(BaseProjectMethodView):
    drf_label = "benthiclit-su"
    project_policy = "data_policy_benthiclit"
    serializer_class = BenthicLITMethodSUSerializer
    serializer_class_geojson = BenthicLITMethodSUGeoSerializer
    serializer_class_csv = BenthicLITMethodSUCSVSerializer
    filterset_class = BenthicLITMethodSUFilterSet
    queryset = BenthicLITSUView.objects.exclude(project_status=Project.TEST).order_by(
        "site_name", "sample_date", "transect_number"
    )


class BenthicLITProjectMethodSEView(BaseProjectMethodView):
    drf_label = "benthiclit-se"
    project_policy = "data_policy_benthiclit"
    permission_classes = [
        Or(ProjectDataReadOnlyPermission, ProjectPublicSummaryPermission)
    ]
    serializer_class = BenthicLITMethodSESerializer
    serializer_class_geojson = BenthicLITMethodSEGeoSerializer
    serializer_class_csv = BenthicLITMethodSESerializer
    filterset_class = BenthicLITMethodSEFilterSet
    queryset = BenthicLITSEView.objects.exclude(project_status=Project.TEST).order_by(
        "site_name", "sample_date"
    )
