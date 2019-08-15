from django.db import transaction
from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import action

from ...models.mermaid import HabitatComplexity, ObsHabitatComplexity

from . import *
from ..sample_event import SampleEventSerializer
from ..benthic_transect import BenthicTransectSerializer
from ..habitat_complexity import HabitatComplexitySerializer
from ..observer import ObserverSerializer
from ..obs_habitat_complexity import ObsHabitatComplexitySerializer
from ..base import BaseProjectApiViewSet


class HabitatComplexityMethodSerializer(HabitatComplexitySerializer):
    sample_event = SampleEventSerializer(source='transect.sample_event')
    benthic_transect = BenthicTransectSerializer(source='transect')
    observers = ObserverSerializer(many=True)
    obs_habitat_complexities = ObsHabitatComplexitySerializer(
        many=True, source='habitatcomplexity_set')

    class Meta:
        model = HabitatComplexity
        exclude = []


class ObsHabitatComplexityReportSerializer(SampleEventReportSerializer, metaclass=SampleEventReportSerializerMeta):
    transect_method = 'habitatcomplexity'
    sample_event_path = '{}__transect__sample_event'.format(transect_method)
    
    idx = 24
    obs_fields = [
        (6, ReportField("habitatcomplexity__transect__reef_slope__name", "Reef slope")),
        (idx, ReportField("habitatcomplexity__transect__number", "Transect number")),
        (idx + 1, ReportField("habitatcomplexity__transect__label", "Transect label")),
        (idx + 2, ReportField("habitatcomplexity__transect__len_surveyed", "Transect length surveyed")),
        (idx + 4, ReportField('interval', 'Interval (m)')),
        (idx + 5, ReportField('score__name', 'Habitat complexity')),
        (idx + 9, ReportField("habitatcomplexity__transect__notes", "Observation notes"))
    ]

    non_field_columns = (
        'habitatcomplexity_id',
        'habitatcomplexity__transect__sample_event__site__project_id',
        'habitatcomplexity__transect__sample_event__management_id'
    )

    class Meta:
        model = HabitatComplexity


class HabitatComplexityMethodView(BaseProjectApiViewSet):
    queryset = HabitatComplexity.objects.select_related(
        'transect', 'transect__sample_event').all().order_by("updated_on", "id")
    serializer_class = HabitatComplexityMethodSerializer
    http_method_names = ['get', 'put', 'head', 'delete']

    @transaction.atomic
    def update(self, request, project_pk, pk=None):
        errors = {}
        is_valid = True
        nested_data = dict(
            sample_event=request.data.get('sample_event'),
            benthic_transect=request.data.get('benthic_transect'),
            observers=request.data.get('observers'),
            obs_habitat_complexities=request.data.get('obs_habitat_complexities')
        )
        habitat_complexity_data = {k: v for k, v in request.data.items()
                                   if k not in nested_data}
        habitat_complexity_id = habitat_complexity_data['id']

        context = dict(request=request)

        # Save models in a transaction
        sid = transaction.savepoint()
        try:
            habitat_complexity = HabitatComplexity.objects.get(id=habitat_complexity_id)

            # Observers
            check, errs = save_one_to_many(
                foreign_key=('transectmethod', habitat_complexity_id),
                database_records=habitat_complexity.observers.all(),
                data=request.data.get('observers') or [],
                serializer_class=ObserverSerializer,
                context=context)
            if check is False:
                is_valid = False
                errors['observers'] = errs

            # Observations
            check, errs = save_one_to_many(
                foreign_key=('habitatcomplexity', habitat_complexity_id),
                database_records=habitat_complexity.habitatcomplexity_set.all(),
                data=request.data.get('obs_habitat_complexities') or [],
                serializer_class=ObsHabitatComplexitySerializer,
                context=context)
            if check is False:
                is_valid = False
                errors['obs_habitat_complexities'] = errs

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

            # Habitat Complexity
            check, errs = save_model(
                data=habitat_complexity_data,
                serializer_class=HabitatComplexitySerializer,
                context=context
            )
            if check is False:
                is_valid = False
                errors['habitat_complexity'] = errs

            if is_valid is False:
                transaction.savepoint_rollback(sid)
                return Response(
                    data=errors,
                    status=status.HTTP_400_BAD_REQUEST
                )

            transaction.savepoint_commit(sid)

            habitat_complexity = HabitatComplexity.objects.get(id=habitat_complexity_id)
            return Response(
                HabitatComplexityMethodSerializer(habitat_complexity).data,
                status=status.HTTP_200_OK
            )

        except:
            transaction.savepoint_rollback(sid)
            raise

    @action(detail=False, methods=['get'])
    def fieldreport(self, request, *args, **kwargs):
        return fieldreport(
            self, request, *args,
            model_cls=ObsHabitatComplexity,
            serializer_class=ObsHabitatComplexityReportSerializer,
            fk='habitatcomplexity',
            order_by=(
                "Site",
                "Transect number",
                "Transect label",
            ),
            **kwargs
        )
