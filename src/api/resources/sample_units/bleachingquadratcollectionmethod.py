from api.models.mermaid import BleachingQuadratCollection
from api import utils
from django.db import transaction
from rest_framework import status
from rest_framework.decorators import list_route
from rest_framework.response import Response

from . import *
from ..base import BaseAPIFilterSet, BaseAPISerializer, BaseProjectApiViewSet
from api.models.mermaid import ObsColoniesBleached, ObsQuadratBenthicPercent
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


class ObsColoniesBleachedReportSerializer(SampleEventReportSerializer):
    __metaclass__ = SampleEventReportSerializerMeta

    transect_method = "bleachingquadratcollection"
    sample_event_path = "{}__quadrat__sample_event".format(transect_method)
    obs_fields = [
        (
            6,
            ReportField(
                "bleachingquadratcollection__quadrat__quadrat_size", "Quadrat size"
            ),
        ),
        (
            23,
            ReportField(
                "bleachingquadratcollection__quadrat__label", "Quadrat collection label"
            ),
        ),
        (28, ReportField("attribute__name", "Benthic attribute")),
        (29, ReportField("growth_form__name", "Growth form")),
        (30, ReportField("count_normal", "Normal count")),
        (31, ReportField("count_pale", "Pale count")),
        (32, ReportField("count_20", "0-20% bleached count")),
        (33, ReportField("count_50", "20-50% bleached count")),
        (34, ReportField("count_80", "50-80% bleached count")),
        (35, ReportField("count_100", "80-100% bleached count")),
        (36, ReportField("count_dead", "Recently dead count")),
        (
            37,
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


class ObsQuadratBenthicPercentReportSerializer(SampleEventReportSerializer):
    __metaclass__ = SampleEventReportSerializerMeta

    transect_method = "bleachingquadratcollection"
    sample_event_path = "{}__quadrat__sample_event".format(transect_method)
    obs_fields = [
        (
            6,
            ReportField(
                "bleachingquadratcollection__quadrat__quadrat_size", "Quadrat size"
            ),
        ),
        (
            23,
            ReportField(
                "bleachingquadratcollection__quadrat__label", "Quadrat collection label"
            ),
        ),
        (28, ReportField("quadrat_number", "Quadrat number")),
        (29, ReportField("percent_hard", "Hard coral (% cover)")),
        (30, ReportField("percent_soft", "Soft coral (% cover)")),
        (31, ReportField("percent_algae", "Macroalgae (% cover)")),
        (
            32,
            ReportField(
                "bleachingquadratcollection__quadrat__notes", "Observation notes"
            ),
        ),
        (32, ReportMethodField("Number of quadrats", quadrat_count)),
        (33, ReportMethodField("Average Hard Coral (% cover)", avg_hard_coral)),
        (34, ReportMethodField("Average Soft Coral (% cover)", avg_soft_coral)),
        (35, ReportMethodField("Average Macroalgae (% cover)", avg_macroalgae)),
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

    @list_route(methods=["get"])
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
