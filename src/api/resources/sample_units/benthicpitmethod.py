from django.db import transaction
from rest_framework import status
from rest_framework.decorators import list_route
from rest_framework.response import Response

from api.models.mermaid import BenthicPIT, ObsBenthicPIT, BenthicAttribute

from . import *
from ..sample_event import SampleEventSerializer
from ..benthic_transect import BenthicTransectSerializer
from ..benthic_pit import BenthicPITSerializer
from ..observer import ObserverSerializer
from ..obs_benthic_pit import ObsBenthicPITSerializer
from ..base import BaseProjectApiViewSet


class BenthicPITMethodSerializer(BenthicPITSerializer):
    sample_event = SampleEventSerializer(source='transect.sample_event')
    benthic_transect = BenthicTransectSerializer(source='transect')
    observers = ObserverSerializer(many=True)
    obs_benthic_pits = ObsBenthicPITSerializer(
        many=True, source='obsbenthicpit_set')

    class Meta:
        model = BenthicPIT
        exclude = []


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

    return bc.__unicode__()


class ObsBenthicPITReportSerializer(SampleEventReportSerializer):
    __metaclass__ = SampleEventReportSerializerMeta

    transect_method = 'benthicpit'
    sample_event_path = '{}__transect__sample_event'.format(transect_method)

    idx = 24
    obs_fields = [
        (6, ReportField("benthicpit__transect__reef_slope__name", "Reef slope")),
        (idx, ReportField("benthicpit__transect__number", "Transect number")),
        (idx + 1, ReportField("benthicpit__transect__label", "Transect label")),
        (idx + 2, ReportField("benthicpit__transect__len_surveyed", "Transect length surveyed")),
        (idx + 4, ReportField('interval', 'PIT interval (m)')),
        (idx + 5, ReportMethodField('Benthic category', to_benthic_attribute_category)),
        (idx + 6, ReportField('attribute__name', 'Benthic attribute')),
        (idx + 7, ReportField('growth_form__name', 'Growth form')),
        (idx + 11, ReportField("benthicpit__transect__notes", "Observation notes"))
    ]

    non_field_columns = (
        'benthicpit_id',
        'benthicpit__transect__sample_event__site__project_id',
        'benthicpit__transect__sample_event__management_id',
        'attribute'
    )

    class Meta:
        model = BenthicPIT

    def preserialize(self, queryset=None):
        super(ObsBenthicPITReportSerializer, self).preserialize(queryset=queryset)

        # Transect total lengths
        benthic_categories = BenthicAttribute.objects.all()

        benthic_category_lookup = {
            str(bc.id): dict(
                name = bc.origin.name
            )
            for bc in benthic_categories
        }

        if len(benthic_category_lookup.keys()) > 0:
            self.serializer_cache[
                "benthic-attribute_lookups-categories"
            ] = benthic_category_lookup


class BenthicPITMethodView(BaseProjectApiViewSet):
    queryset = BenthicPIT.objects.select_related(
        'transect', 'transect__sample_event').all().order_by("updated_on", "id")
    serializer_class = BenthicPITMethodSerializer
    http_method_names = ['get', 'put', 'head', 'delete']

    @transaction.atomic
    def update(self, request, project_pk, pk=None):
        errors = {}
        is_valid = True
        nested_data = dict(
            sample_event=request.data.get('sample_event'),
            benthic_transect=request.data.get('benthic_transect'),
            observers=request.data.get('observers'),
            obs_benthic_pits=request.data.get('obs_benthic_pits')
        )
        benthic_pit_data = {k: v for k, v in request.data.items()
                            if k not in nested_data}
        benthic_pit_id = benthic_pit_data['id']

        context = dict(request=request)

        # Save models in a transaction
        sid = transaction.savepoint()
        try:
            benthic_pit = BenthicPIT.objects.get(id=benthic_pit_id)

            # Observers
            check, errs = save_one_to_many(
                foreign_key=('transectmethod', benthic_pit_id),
                database_records=benthic_pit.observers.all(),
                data=request.data.get('observers') or [],
                serializer_class=ObserverSerializer,
                context=context)
            if check is False:
                is_valid = False
                errors['observers'] = errs

            # Observations
            check, errs = save_one_to_many(
                foreign_key=('benthicpit', benthic_pit_id),
                database_records=benthic_pit.obsbenthicpit_set.all(),
                data=request.data.get('obs_benthic_pits') or [],
                serializer_class=ObsBenthicPITSerializer,
                context=context)
            if check is False:
                is_valid = False
                errors['obs_benthic_pits'] = errs

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

            # Benthic PIT
            check, errs = save_model(
                data=benthic_pit_data,
                serializer_class=BenthicPITSerializer,
                context=context
            )
            if check is False:
                is_valid = False
                errors['benthic_pit'] = errs

            if is_valid is False:
                transaction.savepoint_rollback(sid)
                return Response(
                    data=errors,
                    status=status.HTTP_400_BAD_REQUEST
                )

            transaction.savepoint_commit(sid)

            benthic_pit = BenthicPIT.objects.get(id=benthic_pit_id)
            return Response(
                BenthicPITMethodSerializer(benthic_pit).data,
                status=status.HTTP_200_OK
            )

        except:
            transaction.savepoint_rollback(sid)
            raise

    @list_route(methods=['get'])
    def fieldreport(self, request, *args, **kwargs):
        return fieldreport(
            self, request, *args,
            model_cls=ObsBenthicPIT,
            serializer_class=ObsBenthicPITReportSerializer,
            fk='benthicpit',
            order_by=(
                "Site",
                "Transect number",
                "Transect label",
            ),
            **kwargs
        )
