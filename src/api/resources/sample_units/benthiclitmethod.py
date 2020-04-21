from django.db import transaction
from django.db.models import Sum
from rest_framework import status
from rest_framework.response import Response

from .. import fieldreport
from ...models.mermaid import BenthicLIT, ObsBenthicLIT, BenthicAttribute

from . import *
from ..sample_event import SampleEventSerializer
from ..benthic_transect import BenthicTransectSerializer
from ..benthic_lit import BenthicLITSerializer
from ..observer import ObserverSerializer
from ..obs_benthic_lit import ObsBenthicLITSerializer
from ..base import BaseProjectApiViewSet


class BenthicLITMethodSerializer(BenthicLITSerializer):
    sample_event = SampleEventSerializer(source='transect.sample_event')
    benthic_transect = BenthicTransectSerializer(source='transect')
    observers = ObserverSerializer(many=True)
    obs_benthic_lits = ObsBenthicLITSerializer(
        many=True, source='obsbenthiclit_set')

    class Meta:
        model = BenthicLIT
        exclude = []


def to_total_lit(field, row, serializer_instance):
    benthiclit_id = row.get('benthiclit_id')
    if benthiclit_id is None:
        return ''

    lookup = serializer_instance.serializer_cache.get("benthiclit_lookups-totals")
    if lookup:
        total = lookup.get(str(benthiclit_id)) or dict()
        return total.get("total_lit") or ''
    else:
        total = ObsBenthicLIT.objects.filter(benthiclit=benthiclit_id)\
            .values('benthiclit_id').annotate(total_lit=Sum('length'))
        return total.total_lit or ''


def _get_benthic_attribute_category(row, serializer_instance):
    benthic_attribute_id = row.get("attribute")
    if benthic_attribute_id is None:
        return None

    lookup = serializer_instance.serializer_cache.get("benthic-attribute_lookups-categories")
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


class ObsBenthicLITReportSerializer(SampleEventReportSerializer, metaclass=SampleEventReportSerializerMeta):
    transect_method = 'benthiclit'
    sample_event_path = '{}__transect__sample_event'.format(transect_method)

    idx = 24
    obs_fields = [
        (6, ReportField("benthiclit__transect__reef_slope__name", "Reef slope")),
        (idx, ReportField("benthiclit__transect__number", "Transect number")),
        (idx + 1, ReportField("benthiclit__transect__label", "Transect label")),
        (idx + 2, ReportField("benthiclit__transect__len_surveyed", "Transect length surveyed")),
        (idx + 4, ReportMethodField('Benthic category', to_benthic_attribute_category)),
        (idx + 5, ReportField('attribute__name', 'Benthic attribute')),
        (idx + 6, ReportField('growth_form__name', 'Growth form')),
        (idx + 7, ReportField('length', 'LIT (cm)')),
        (idx + 8, ReportMethodField('Total transect cm', to_total_lit)),
        (idx + 12, ReportField("benthiclit__transect__notes", "Observation notes"))
    ]

    non_field_columns = (
        'benthiclit_id',
        'benthiclit__transect__sample_event__site__project_id',
        'benthiclit__transect__sample_event__management_id',
        'attribute'
    )

    class Meta:
        model = BenthicLIT

    def preserialize(self, queryset=None):
        super(ObsBenthicLITReportSerializer, self).preserialize(queryset=queryset)

        # Transect total lengths
        transect_totals = queryset.values('benthiclit_id').annotate(total_lit=Sum('length'))
        benthic_categories = BenthicAttribute.objects.all()

        benthic_category_lookup = {
            str(bc.id): dict(
                name = bc.origin.name
            )
            for bc in benthic_categories
        }

        transect_total_lookup = {
            str(tt['benthiclit_id']): dict(
                total_lit=tt['total_lit']
            )
            for tt in transect_totals
        }

        if len(benthic_category_lookup.keys()) > 0:
            self.serializer_cache[
                "benthic-attribute_lookups-categories"
            ] = benthic_category_lookup

        if len(transect_total_lookup.keys()) > 0:
            self.serializer_cache[
                "benthiclit_lookups-totals"
            ] = transect_total_lookup


class BenthicLITMethodView(BaseProjectApiViewSet):
    queryset = BenthicLIT.objects.select_related(
        'transect', 'transect__sample_event').all().order_by("updated_on", "id")
    serializer_class = BenthicLITMethodSerializer
    http_method_names = ['get', 'put', 'head', 'delete']

    @transaction.atomic
    def update(self, request, project_pk, pk=None):
        errors = {}
        is_valid = True
        nested_data = dict(
            sample_event=request.data.get('sample_event'),
            benthic_transect=request.data.get('benthic_transect'),
            observers=request.data.get('observers'),
            obs_benthic_lits=request.data.get('obs_benthic_lits')
        )
        benthic_lit_data = {k: v for k, v in request.data.items()
                            if k not in nested_data}
        benthic_lit_id = benthic_lit_data['id']

        context = dict(request=request)

        # Save models in a transaction
        sid = transaction.savepoint()
        try:
            benthic_lit = BenthicLIT.objects.get(id=benthic_lit_id)

            # Observers
            check, errs = save_one_to_many(
                foreign_key=('transectmethod', benthic_lit_id),
                database_records=benthic_lit.observers.all(),
                data=request.data.get('observers') or [],
                serializer_class=ObserverSerializer,
                context=context)
            if check is False:
                is_valid = False
                errors['observers'] = errs

            # Observations
            check, errs = save_one_to_many(
                foreign_key=('benthiclit', benthic_lit_id),
                database_records=benthic_lit.obsbenthiclit_set.all(),
                data=request.data.get('obs_benthic_lits') or [],
                serializer_class=ObsBenthicLITSerializer,
                context=context)
            if check is False:
                is_valid = False
                errors['obs_benthic_lits'] = errs

            # Sample Event
            check, errs = save_model(
                data=nested_data['sample_event'],
                serializer_class=SampleEventSerializer,
                context=context
            )
            if check is False:
                is_valid = False
                errors['sample_event'] = errs

            # Benthic Transect
            check, errs = save_model(
                data=nested_data['benthic_transect'],
                serializer_class=BenthicTransectSerializer,
                context=context
            )
            if check is False:
                is_valid = False
                errors['benthic_transect'] = errs

            # Benthic LIT
            check, errs = save_model(
                data=benthic_lit_data,
                serializer_class=BenthicLITSerializer,
                context=context
            )
            if check is False:
                is_valid = False
                errors['benthic_lit'] = errs

            if is_valid is False:
                transaction.savepoint_rollback(sid)
                return Response(
                    data=errors,
                    status=status.HTTP_400_BAD_REQUEST
                )

            transaction.savepoint_commit(sid)

            benthic_lit = BenthicLIT.objects.get(id=benthic_lit_id)
            return Response(
                BenthicLITMethodSerializer(benthic_lit).data,
                status=status.HTTP_200_OK
            )

        except:
            transaction.savepoint_rollback(sid)
            raise

    @action(detail=False, methods=['get'])
    def fieldreport(self, request, *args, **kwargs):
        return fieldreport(
            self, request, *args,
            model_cls=ObsBenthicLIT,
            serializer_class=ObsBenthicLITReportSerializer,
            fk='benthiclit',
            order_by=(
                "Site",
                "Transect number",
                "Transect label",
            ),
            **kwargs
        )

