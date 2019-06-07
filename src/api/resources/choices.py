import pytz
from base import BaseChoiceApiViewSet
from django.http.response import HttpResponseBadRequest
from django.utils.dateparse import parse_datetime
from rest_framework.response import Response
from rest_framework.decorators import list_route

from ..models import (BeltTransectWidth, BenthicLifeHistory, CollectRecord,
                      Country, Current, FishGroupFunction, FishGroupSize,
                      FishGroupTrophic, FishSizeBin, FishSpecies, GrowthForm,
                      HabitatComplexityScore, ManagementCompliance,
                      ManagementParty, Project, ProjectProfile, ReefExposure,
                      ReefSlope, ReefType, ReefZone, Region, RelativeDepth,
                      Tide, Visibility)


class ChoiceViewSet(BaseChoiceApiViewSet):

    def get_model_choices(self, model, order_by):
        choices = [c.choice for c in model.objects.all().order_by(order_by)]
        return {'data': choices}

    def get_choices(self):
        belttransectwidths = self.get_model_choices(BeltTransectWidth, 'val')
        benthiclifehistories = self.get_model_choices(BenthicLifeHistory, 'name')
        growthforms = self.get_model_choices(GrowthForm, 'name')
        countries = self.get_model_choices(Country, 'name')
        currents = self.get_model_choices(Current, 'name')
        fishgroupfunctions = self.get_model_choices(FishGroupFunction, 'name')
        fishgrouptrophics = self.get_model_choices(FishGroupTrophic, 'name')
        fishsizebins = self.get_model_choices(FishSizeBin, 'val')
        habitatcomplexityscores = self.get_model_choices(HabitatComplexityScore, 'val')
        managementcompliances = self.get_model_choices(ManagementCompliance, 'name')
        managementparties = self.get_model_choices(ManagementParty, 'name')
        reefexposures = self.get_model_choices(ReefExposure, 'val')
        reefslopes = self.get_model_choices(ReefSlope, 'val')
        reeftypes = self.get_model_choices(ReefType, 'name')
        reefzones = self.get_model_choices(ReefZone, 'name')
        regions = self.get_model_choices(Region, 'name')
        relativedepths = self.get_model_choices(RelativeDepth, 'name')
        tides = self.get_model_choices(Tide, 'name')
        visibilities = self.get_model_choices(Visibility, 'val')

        return {
            'belttransectwidths': belttransectwidths,
            'benthiclifehistories': benthiclifehistories,
            'growthforms': growthforms,
            'countries': countries,
            'currents': currents,
            'datapolicies': {'data': [dict(updated_on=Project.DATA_POLICY_CHOICES_UPDATED_ON, **c) for c in Project.DATA_POLICY_CHOICES]},
            'fishgroupfunctions': fishgroupfunctions,
            'fishgrouptrophics': fishgrouptrophics,
            'fishsizebins': fishsizebins,
            'habitatcomplexityscores': habitatcomplexityscores,
            'managementcompliances': managementcompliances,
            'managementparties': managementparties,
            'reefexposures': reefexposures,
            'reefslopes': reefslopes,
            'reeftypes': reeftypes,
            'reefzones': reefzones,
            'regions': regions,
            'relativedepths': relativedepths,
            'roles': {'data': [{'id': c[0], 'name': c[1], 'updated_on': ProjectProfile.ROLES_UPDATED_ON} for c in ProjectProfile.ROLES]},
            'stages': {'data': [{'id': c[0], 'name': c[1], 'updated_on': CollectRecord.STAGE_CHOICES_UPDATED_ON} for c in CollectRecord.STAGE_CHOICES]},
            'tides': tides,
            'visibilities': visibilities,
        }

    def _get_newest_timestamp(self, choices):
        return max([c["updated_on"] for c in choices.get("data") if c.get("updated_on")])

    @list_route(methods=["GET"])
    def updates(self, request, *args, **kwargs):
        added = []
        modified = []
        removed = []

        qp_timestamp = request.query_params.get("timestamp")
        if qp_timestamp is None:
            return HttpResponseBadRequest()

        try:
            timestamp = parse_datetime(qp_timestamp)
        except ValueError:
            timestamp = None

        if timestamp:
            timestamp = timestamp.replace(tzinfo=pytz.utc)

        choices = self.get_choices()
        for key, choice_set in choices.items():
            choice_timestamp = self._get_newest_timestamp(choice_set)
            if choice_timestamp is None or timestamp is None or choice_timestamp > timestamp:
                modified.append(dict(name=key, **choice_set))
        return Response(dict(added=added, modified=modified, removed=removed))
