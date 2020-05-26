from api import utils
from django.db import transaction
from rest_framework import status
from rest_framework.response import Response
from rest_framework.serializers import SerializerMethodField

from . import *
from .. import fieldreport
from ...models.mermaid import BleachingQuadratCollection, ObsColoniesBleached, ObsQuadratBenthicPercent
from ...models.view_models import (
    BleachingQCColoniesBleachedObsView,
    BleachingQCQuadratBenthicPercentObsView,
    BleachingQCSUView,
    BleachingQCSEView
)

from ..base import (
    BaseProjectApiViewSet,
    BaseViewAPISerializer,
    BaseViewAPIGeoSerializer,
    BaseTransectFilterSet,
)
from ..bleaching_quadrat_collection import BleachingQuadratCollectionSerializer
from ..obs_colonies_bleached import ObsColoniesBleachedSerializer
from ..obs_quadrat_benthic_percent import ObsQuadratBenthicPercentSerializer
from ..observer import ObserverSerializer
from ..quadrat_collection import QuadratCollectionSerializer
from ..sample_event import SampleEventSerializer


def avg_hard_coral(field, row, serializer_instance):
    pk = str(row["bleachingquadratcollection_id"])
    val = serializer_instance.serializer_cache["quadrat_percent_summary_stats"][pk][
        "avg_hard_coral"
    ]
    if val is None:
        return ''
    return '{0:.1f}'.format(val)


def avg_soft_coral(field, row, serializer_instance):
    pk = str(row["bleachingquadratcollection_id"])
    val = serializer_instance.serializer_cache["quadrat_percent_summary_stats"][pk][
        "avg_soft_coral"
    ]
    if val is None:
        return ''
    return '{0:.1f}'.format(val)


def avg_macroalgae(field, row, serializer_instance):
    pk = str(row["bleachingquadratcollection_id"])
    val = serializer_instance.serializer_cache["quadrat_percent_summary_stats"][pk][
        "avg_macroalgae"
    ]
    if val is None:
        return ''
    return '{0:.1f}'.format(val)


def quadrat_count(field, row, serializer_instance):
    pk = str(row["bleachingquadratcollection_id"])
    return serializer_instance.serializer_cache["quadrat_percent_summary_stats"][pk][
        "quadrat_count"
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


class ObsColoniesBleachedReportSerializer(SampleEventReportSerializer, metaclass=SampleEventReportSerializerMeta):
    transect_method = "bleachingquadratcollection"
    sample_event_path = "{}__quadrat__sample_event".format(transect_method)
    idx = 25
    obs_fields = [
        (
            6,
            ReportField(
                "bleachingquadratcollection__quadrat__quadrat_size", "Quadrat size"
            ),
        ),
        (
            idx,
            ReportField(
                "bleachingquadratcollection__quadrat__label", "Quadrat collection label"
            ),
        ),
        (idx + 5, ReportField("attribute__name", "Benthic attribute")),
        (idx + 6, ReportField("growth_form__name", "Growth form")),
        (idx + 7, ReportField("count_normal", "Normal count")),
        (idx + 8, ReportField("count_pale", "Pale count")),
        (idx + 9, ReportField("count_20", "0-20% bleached count")),
        (idx + 10, ReportField("count_50", "20-50% bleached count")),
        (idx + 11, ReportField("count_80", "50-80% bleached count")),
        (idx + 12, ReportField("count_100", "80-100% bleached count")),
        (idx + 13, ReportField("count_dead", "Recently dead count")),
        (
            idx + 14,
            ReportField(
                "bleachingquadratcollection__quadrat__notes", "Observation notes"
            ),
        ),
    ]

    non_field_columns = (
        "bleachingquadratcollection_id",
        "bleachingquadratcollection__quadrat__sample_event__site__project_id",
        "bleachingquadratcollection__quadrat__sample_event__management_id",
        "attribute",
    )

    class Meta:
        model = ObsColoniesBleached

    def preserialize(self, queryset=None):
        super(ObsColoniesBleachedReportSerializer, self).preserialize(queryset=queryset)


class ObsQuadratBenthicPercentReportSerializer(SampleEventReportSerializer, metaclass=SampleEventReportSerializerMeta):
    transect_method = "bleachingquadratcollection"
    sample_event_path = "{}__quadrat__sample_event".format(transect_method)
    idx = 25
    obs_fields = [
        (
            6,
            ReportField(
                "bleachingquadratcollection__quadrat__quadrat_size", "Quadrat size"
            ),
        ),
        (
            idx,
            ReportField(
                "bleachingquadratcollection__quadrat__label", "Quadrat collection label"
            ),
        ),
        (idx + 5, ReportField("quadrat_number", "Quadrat number")),
        (idx + 6, ReportField("percent_hard", "Hard coral (% cover)")),
        (idx + 7, ReportField("percent_soft", "Soft coral (% cover)")),
        (idx + 8, ReportField("percent_algae", "Macroalgae (% cover)")),
        (
            idx + 9,
            ReportField(
                "bleachingquadratcollection__quadrat__notes", "Observation notes"
            ),
        ),
        (idx + 10, ReportMethodField("Number of quadrats", quadrat_count)),
        (idx + 11, ReportMethodField("Average Hard Coral (% cover)", avg_hard_coral)),
        (idx + 12, ReportMethodField("Average Soft Coral (% cover)", avg_soft_coral)),
        (idx + 13, ReportMethodField("Average Macroalgae (% cover)", avg_macroalgae)),
    ]

    non_field_columns = (
        "bleachingquadratcollection_id",
        "bleachingquadratcollection__quadrat__sample_event__site__project_id",
        "bleachingquadratcollection__quadrat__sample_event__management_id",
    )

    class Meta:
        model = ObsQuadratBenthicPercent

    def preserialize(self, queryset=None):
        super(ObsQuadratBenthicPercentReportSerializer, self).preserialize(
            queryset=queryset
        )

        stats = dict()
        for rec in queryset:
            pk = str(rec.get("bleachingquadratcollection_id"))
            if pk not in stats:
                stats[pk] = dict(
                    quadrat_count=0,
                    percent_hards=[],
                    percent_softs=[],
                    percent_algaes=[]
                )
            stats[pk]["quadrat_count"] += 1
            stats[pk]["percent_hards"].append(rec.get("percent_hard"))
            stats[pk]["percent_softs"].append(rec.get("percent_soft"))
            stats[pk]["percent_algaes"].append(rec.get("percent_algae"))

        quadrat_percent_summary_stats = dict()
        for pk, s in stats.items():
            cnt = s.get("quadrat_count")
            quadrat_percent_summary_stats[pk] = dict(
                quadrat_count=cnt,
                avg_hard_coral=utils.safe_division(utils.safe_sum(*s["percent_hards"]), cnt),
                avg_soft_coral=utils.safe_division(utils.safe_sum(*s["percent_softs"]), cnt),
                avg_macroalgae=utils.safe_division(utils.safe_sum(*s["percent_algaes"]), cnt),
            )

        self.serializer_cache["quadrat_percent_summary_stats"] = quadrat_percent_summary_stats


class BleachingQuadratCollectionMethodView(BaseProjectApiViewSet):
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
        bleaching_qc_data = {
            k: v for k, v in request.data.items() if k not in nested_data
        }
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

            transaction.savepoint_commit(sid)
            bleaching_qc = BleachingQuadratCollection.objects.get(id=bleaching_qc_id)
            return Response(
                BleachingQuadratCollectionMethodSerializer(bleaching_qc).data,
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
            model_cls=[ObsColoniesBleached, ObsQuadratBenthicPercent],
            serializer_class=[
                ObsColoniesBleachedReportSerializer,
                ObsQuadratBenthicPercentReportSerializer,
            ],
            fk="bleachingquadratcollection",
            order_by=("Site", "Quadrat collection label"),
            **kwargs
        )


class BleachingQCMethodObsColoniesBleachedSerializer(BaseViewAPISerializer):
    class Meta(BaseViewAPISerializer.Meta):
        model = BleachingQCColoniesBleachedObsView
        exclude = BaseViewAPISerializer.Meta.exclude.copy()
        exclude.append("location")
        header_order = ["id"] + BaseViewAPISerializer.Meta.header_order.copy()
        header_order.extend(
            [
                "sample_unit_id",
                "sample_time",
                "label",
                "depth",
                "observers",
                "data_policy_bleachingqc",
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
        )


class BleachingQCMethodObsColoniesBleachedCSVSerializer(BleachingQCMethodObsColoniesBleachedSerializer):
    observers = SerializerMethodField()


class BleachingQCMethodObsColoniesBleachedGeoSerializer(BaseViewAPIGeoSerializer):
    class Meta(BaseViewAPIGeoSerializer.Meta):
        model = BleachingQCColoniesBleachedObsView


class BleachingQCMethodColoniesBleachedObsFilterSet(BaseTransectFilterSet):

    class Meta:
        model = BleachingQCColoniesBleachedObsView


class BleachingQCProjectMethodObsColoniesBleachedView(BaseProjectMethodView):
    drf_label = "bleachingqc-coloniesbleached"
    project_policy = "data_policy_bleachingqc"
    serializer_class = BleachingQCMethodObsColoniesBleachedSerializer
    serializer_class_geojson = BleachingQCMethodObsColoniesBleachedGeoSerializer
    serializer_class_csv = BleachingQCMethodObsColoniesBleachedCSVSerializer
    filterset_class = BleachingQCMethodColoniesBleachedObsFilterSet
    queryset = BleachingQCColoniesBleachedObsView.objects.exclude(project_status=Project.TEST).order_by(
        "site_name", "sample_date", "label", "benthic_attribute", "growth_form"
    )


# class BleachingQCMethodObsQuadratBenthicPercentSerializer(BaseViewAPISerializer):


# class BleachingQCMethodObsQuadratBenthicPercentCSVSerializer(BaseViewAPISerializer):


# class BleachingQCMethodObsQuadratBenthicPercentGeoSerializer(BaseViewAPISerializer):


# class BleachingQCMethodQuadratBenthicPercentObsFilterSet(BaseTransectFilterSet):


# class BleachingQCMethodObsQuadratBenthicPercentView(BaseProjectMethodView):


# class BleachingQCMethodSUSerializer(BaseViewAPISerializer):


# class BleachingQCMethodSUCSVSerializer(BaseViewAPISerializer):


# class BleachingQCMethodSUGeoSerializer(BaseViewAPISerializer):


# class BleachingQCMethodSESerializer(BaseViewAPISerializer):


# class BleachingQCMethodSEGeoSerializer(BaseViewAPISerializer):


# class BleachingQCMethodSUFilterSet(BaseTransectFilterSet):


# class BleachingQCMethodSEFilterSet(BaseTransectFilterSet):


# class BleachingQCProjectMethodSUView(BaseProjectMethodView):


# class BleachingQCProjectMethodSEView(BaseProjectMethodView):

