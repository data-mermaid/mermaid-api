from django.db import transaction
from rest_framework import status
from rest_framework.response import Response
from rest_framework.serializers import SerializerMethodField
from django_filters import BaseInFilter, RangeFilter

# from .. import fieldreport
from ...models.mermaid import BenthicPIT, ObsBenthicPIT, BenthicAttribute
from ...models.view_models import BenthicPITObsView, BenthicPITSUView, BenthicPITSEView

from . import *
from ..base import (
    BaseProjectApiViewSet,
    BaseViewAPISerializer,
    BaseViewAPIGeoSerializer,
    BaseTransectFilterSet,
)
from ..benthic_pit import BenthicPITSerializer
from ..benthic_transect import BenthicTransectSerializer
from ..obs_benthic_pit import ObsBenthicPITSerializer
from ..observer import ObserverSerializer
from ..sample_event import SampleEventSerializer


class BenthicPITMethodSerializer(BenthicPITSerializer):
    sample_event = SampleEventSerializer(source="transect.sample_event")
    benthic_transect = BenthicTransectSerializer(source="transect")
    observers = ObserverSerializer(many=True)
    obs_benthic_pits = ObsBenthicPITSerializer(many=True, source="obsbenthicpit_set")

    class Meta:
        model = BenthicPIT
        exclude = []


def _get_benthic_attribute_category(row, serializer_instance):
    benthic_attribute_id = row.get("attribute")
    if benthic_attribute_id is None:
        return None

    lookup = serializer_instance.serializer_cache.get(
        "benthic-attribute_lookups-categories"
    )
    if lookup:
        return lookup.get(str(benthic_attribute_id)) or dict()
    else:
        return BenthicAttribute.objects.get(id=benthic_attribute_id)


def to_benthic_attribute_category(field, row, serializer_instance):
    bc = _get_benthic_attribute_category(row, serializer_instance)

    if bc is None:
        return ""

    elif isinstance(bc, dict):
        return bc.get("name") or ""

    return str(bc)


# class ObsBenthicPITReportSerializer(
#     SampleEventReportSerializer, metaclass=SampleEventReportSerializerMeta
# ):
#     transect_method = "benthicpit"
#     sample_event_path = "{}__transect__sample_event".format(transect_method)

#     idx = 24
#     obs_fields = [
#         (6, ReportField("benthicpit__transect__reef_slope__name", "Reef slope")),
#         (idx, ReportField("benthicpit__transect__number", "Transect number")),
#         (idx + 1, ReportField("benthicpit__transect__label", "Transect label")),
#         (
#             idx + 2,
#             ReportField(
#                 "benthicpit__transect__len_surveyed", "Transect length surveyed"
#             ),
#         ),
#         (idx + 4, ReportField("interval", "PIT interval (m)")),
#         (idx + 5, ReportMethodField("Benthic category", to_benthic_attribute_category)),
#         (idx + 6, ReportField("attribute__name", "Benthic attribute")),
#         (idx + 7, ReportField("growth_form__name", "Growth form")),
#         (idx + 11, ReportField("benthicpit__transect__notes", "Observation notes")),
#     ]

#     non_field_columns = (
#         "benthicpit_id",
#         "benthicpit__transect__sample_event__site__project_id",
#         "benthicpit__transect__sample_event__management_id",
#         "attribute",
#     )

#     class Meta:
#         model = BenthicPIT

#     def preserialize(self, queryset=None):
#         super(ObsBenthicPITReportSerializer, self).preserialize(queryset=queryset)

#         # Transect total lengths
#         benthic_categories = BenthicAttribute.objects.all()

#         benthic_category_lookup = {
#             str(bc.id): dict(name=bc.origin.name) for bc in benthic_categories
#         }

#         if len(benthic_category_lookup.keys()) > 0:
#             self.serializer_cache[
#                 "benthic-attribute_lookups-categories"
#             ] = benthic_category_lookup


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

    # @action(detail=False, methods=["get"])
    # def fieldreport(self, request, *args, **kwargs):
    #     return fieldreport(
    #         self,
    #         request,
    #         *args,
    #         model_cls=ObsBenthicPIT,
    #         serializer_class=ObsBenthicPITReportSerializer,
    #         fk="benthicpit",
    #         order_by=("Site", "Transect number", "Transect label"),
    #         **kwargs
    #     )


class BenthicPITMethodObsSerializer(BaseViewAPISerializer):
    class Meta(BaseViewAPISerializer.Meta):
        model = BenthicPITObsView
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
                "data_policy_benthicpit",
                "interval_size",
                "interval_start",
                "interval",
                "benthic_category",
                "benthic_attribute",
                "growth_form",
                "observation_notes",
            ]
        )


class BenthicPITMethodObsCSVSerializer(BenthicPITMethodObsSerializer):
    observers = SerializerMethodField()


class BenthicPITMethodObsGeoSerializer(BaseViewAPIGeoSerializer):
    class Meta(BaseViewAPIGeoSerializer.Meta):
        model = BenthicPITObsView


class BenthicPITMethodSUSerializer(BaseViewAPISerializer):
    class Meta(BaseViewAPISerializer.Meta):
        model = BenthicPITSUView
        exclude = BaseViewAPISerializer.Meta.exclude.copy()
        exclude.append("location")
        header_order = BaseViewAPISerializer.Meta.header_order.copy()
        header_order.extend(
            [
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


class BenthicPITMethodSUCSVSerializer(BenthicPITMethodSUSerializer):
    observers = SerializerMethodField()


class BenthicPITMethodSUGeoSerializer(BaseViewAPIGeoSerializer):
    class Meta(BaseViewAPIGeoSerializer.Meta):
        model = BenthicPITSUView


class BenthicPITMethodSESerializer(BaseViewAPISerializer):
    class Meta(BaseViewAPISerializer.Meta):
        model = BenthicPITSEView
        exclude = BaseViewAPISerializer.Meta.exclude.copy()
        exclude.append("location")
        header_order = BaseViewAPISerializer.Meta.header_order.copy()
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


class BenthicPITMethodObsFilterSet(BaseTransectFilterSet):
    depth = RangeFilter()
    sample_unit_id = BaseInFilter(method="id_lookup")
    observers = BaseInFilter(method="json_name_lookup")
    transect_len_surveyed = RangeFilter()
    reef_slope = BaseInFilter(method="char_lookup")
    interval_size = RangeFilter()
    interval = RangeFilter()

    class Meta:
        model = BenthicPITObsView
        fields = [
            "depth",
            "sample_unit_id",
            "observers",
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


class BenthicPITMethodSUFilterSet(BaseTransectFilterSet):
    transect_len_surveyed = RangeFilter()
    depth = RangeFilter()
    observers = BaseInFilter(method="json_name_lookup")
    reef_slope = BaseInFilter(method="char_lookup")
    interval_size = RangeFilter()

    class Meta:
        model = BenthicPITSUView
        fields = [
            "depth",
            "observers",
            "transect_len_surveyed",
            "reef_slope",
            "transect_number",
            "interval_size",
            "data_policy_benthicpit",
        ]


class BenthicPITMethodSEFilterSet(BaseTransectFilterSet):
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
    serializer_class_csv = BenthicPITMethodObsCSVSerializer
    filterset_class = BenthicPITMethodObsFilterSet
    queryset = BenthicPITObsView.objects.exclude(project_status=Project.TEST).order_by(
        "site_name", "sample_date", "transect_number", "label", "interval"
    )


class BenthicPITProjectMethodSUView(BaseProjectMethodView):
    drf_label = "benthicpit-su"
    project_policy = "data_policy_benthicpit"
    serializer_class = BenthicPITMethodSUSerializer
    serializer_class_geojson = BenthicPITMethodSUGeoSerializer
    serializer_class_csv = BenthicPITMethodSUCSVSerializer
    filterset_class = BenthicPITMethodSUFilterSet
    queryset = BenthicPITSUView.objects.exclude(project_status=Project.TEST).order_by(
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
    serializer_class_csv = BenthicPITMethodSESerializer
    filterset_class = BenthicPITMethodSEFilterSet
    queryset = BenthicPITSEView.objects.exclude(project_status=Project.TEST).order_by(
        "site_name", "sample_date"
    )
