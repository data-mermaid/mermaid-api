from operator import itemgetter

import pytz
from django.http.response import HttpResponseBadRequest
from django.utils.dateparse import parse_datetime
from natsort import natsorted
from rest_framework.decorators import action
from rest_framework.response import Response

from ..models import (
    BeltTransectWidth,
    BenthicLifeHistory,
    CollectRecord,
    Country,
    Current,
    FishGroupFunction,
    FishGroupSize,
    FishGroupTrophic,
    FishSizeBin,
    FishSpecies,
    GFCRIndicatorSet,
    GFCRFinanceSolution,
    GFCRInvestmentSource,
    GFCRRevenue,
    GrowthForm,
    HabitatComplexityScore,
    ManagementCompliance,
    ManagementParty,
    Project,
    ProjectProfile,
    ReefExposure,
    ReefSlope,
    ReefType,
    ReefZone,
    Region,
    RelativeDepth,
    Tide,
    Visibility,
)
from .base import BaseChoiceApiViewSet


class ChoiceViewSet(BaseChoiceApiViewSet):
    def get_choices(self):
        belttransectwidths = dict(data=BeltTransectWidth.objects.choices(order_by="name"))
        benthiclifehistories = dict(data=BenthicLifeHistory.objects.choices(order_by="name"))
        growthforms = dict(data=GrowthForm.objects.choices(order_by="name"))
        countries = dict(data=Country.objects.choices(order_by="name"))
        currents = dict(data=Current.objects.choices(order_by="val"))
        fishgroupfunctions = dict(data=FishGroupFunction.objects.choices(order_by="name"))
        fishgrouptrophics = dict(data=FishGroupTrophic.objects.choices(order_by="name"))
        fishgroupsizes = dict(data=FishGroupSize.objects.choices(order_by="name"))
        fishsizebins = dict(data=FishSizeBin.objects.choices(order_by="val"))
        fishsizebins["data"] = natsorted(fishsizebins["data"], key=itemgetter(*["name"]))
        habitatcomplexityscores = dict(data=HabitatComplexityScore.objects.choices(order_by="val"))
        managementcompliances = dict(data=ManagementCompliance.objects.choices(order_by="name"))
        managementparties = dict(data=ManagementParty.objects.choices(order_by="name"))
        reefexposures = dict(data=ReefExposure.objects.choices(order_by="val"))
        reefslopes = dict(data=ReefSlope.objects.choices(order_by="val"))
        reeftypes = dict(data=ReefType.objects.choices(order_by="name"))
        reefzones = dict(data=ReefZone.objects.choices(order_by="name"))
        regions = dict(data=Region.objects.choices(order_by="name"))
        relativedepths = dict(data=RelativeDepth.objects.choices(order_by="-name"))
        tides = dict(data=Tide.objects.choices(order_by="val"))
        visibilities = dict(data=Visibility.objects.choices(order_by="val"))

        return {
            "belttransectwidths": belttransectwidths,
            "benthiclifehistories": benthiclifehistories,
            "growthforms": growthforms,
            "countries": countries,
            "currents": currents,
            "datapolicies": {
                "data": [
                    dict(updated_on=Project.DATA_POLICY_CHOICES_UPDATED_ON, **c)
                    for c in Project.DATA_POLICY_CHOICES
                ]
            },
            "fishgroupfunctions": fishgroupfunctions,
            "fishgroupsizes": fishgroupsizes,
            "fishgrouptrophics": fishgrouptrophics,
            "fishsizebins": fishsizebins,
            "habitatcomplexityscores": habitatcomplexityscores,
            "indicatorsettypes": {
                "data": [
                    {
                        "id": c[0],
                        "name": c[1],
                        "updated_on": GFCRIndicatorSet.INDICATOR_SET_TYPE_CHOICES_UPDATED_ON,
                    }
                    for c in GFCRIndicatorSet.INDICATOR_SET_TYPE_CHOICES
                ]
            },
            "investmentsources": {
                "data": [
                    {
                        "id": c[0],
                        "name": c[1],
                        "updated_on": GFCRInvestmentSource.INVESTMENT_SOURCE_CHOICES_UPDATED_ON,
                    }
                    for c in GFCRInvestmentSource.INVESTMENT_SOURCE_CHOICES
                ]
            },
            "investmenttypes": {
                "data": [
                    {
                        "id": c[0],
                        "name": c[1],
                        "updated_on": GFCRInvestmentSource.INVESTMENT_TYPE_CHOICES_UPDATED_ON,
                    }
                    for c in GFCRInvestmentSource.INVESTMENT_TYPE_CHOICES
                ]
            },
            "lengthtypes": {
                "data": [
                    {
                        "id": c[0],
                        "name": c[1],
                        "updated_on": FishSpecies.LENGTH_TYPES_CHOICES_UPDATED_ON,
                    }
                    for c in FishSpecies.LENGTH_TYPES
                ]
            },
            "managementcompliances": managementcompliances,
            "managementparties": managementparties,
            "reefexposures": reefexposures,
            "reefslopes": reefslopes,
            "reeftypes": reeftypes,
            "reefzones": reefzones,
            "regions": regions,
            "relativedepths": relativedepths,
            "revenuetypes": {
                "data": [
                    {
                        "id": c[0],
                        "name": c[1],
                        "updated_on": GFCRRevenue.REVENUE_TYPE_CHOICES_UPDATED_ON,
                    }
                    for c in GFCRRevenue.REVENUE_TYPE_CHOICES
                ]
            },
            "roles": {
                "data": [
                    {
                        "id": c[0],
                        "name": c[1],
                        "updated_on": ProjectProfile.ROLES_UPDATED_ON,
                    }
                    for c in ProjectProfile.ROLES
                ]
            },
            "sectors": {
                "data": [
                    {
                        "id": c[0],
                        "name": c[1],
                        "updated_on": GFCRFinanceSolution.SECTOR_CHOICES_UPDATED_ON,
                    }
                    for c in GFCRFinanceSolution.SECTOR_CHOICES
                ]
            },
            "stages": {
                "data": [
                    {
                        "id": c[0],
                        "name": c[1],
                        "updated_on": CollectRecord.STAGE_CHOICES_UPDATED_ON,
                    }
                    for c in CollectRecord.STAGE_CHOICES
                ]
            },
            "sustainablefinancemechanisms": {
                "data": [
                    {
                        "id": c[0],
                        "name": c[1],
                        "updated_on": GFCRFinanceSolution.SUSTAINABLE_FINANCE_MECHANISM_CHOICES_UPDATED_ON,
                    }
                    for c in GFCRFinanceSolution.SUSTAINABLE_FINANCE_MECHANISM_CHOICES
                ]
            },
            "tides": tides,
            "visibilities": visibilities,
        }

    def _get_newest_timestamp(self, choices):
        return max([c["updated_on"] for c in choices.get("data") if c.get("updated_on")])

    @action(detail=False, methods=["GET"])
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
