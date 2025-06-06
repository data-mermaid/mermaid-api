import statistics
import uuid
from datetime import datetime

from django.db import transaction
from rest_condition import Or
from rest_framework import serializers, status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from ..models import (
    GFCRFinanceSolution,
    GFCRIndicatorSet,
    GFCRInvestmentSource,
    GFCRRevenue,
    Project,
    RestrictedProjectSummarySampleEvent,
)
from ..permissions import AuthenticatedReadOnlyPermission, ProjectDataAdminPermission
from ..utils.project import (
    citation_retrieved_text,
    default_citation,
    get_profiles,
    suggested_citation,
)
from .base import BaseAPISerializer, BaseProjectApiViewSet

BENTHIC_LIT = "benthiclit"
BENTHIC_PIT = "benthicpit"
BENTHIC_PQT = "benthicpqt"
QUADRAT_BENTHIC_PERCENT = "quadrat_benthic_percent"


def get_quadrat_benthic_percent_averages(protocols_data, protocol):
    percent_cover = protocols_data.get(protocol) or {}
    hard_coral = percent_cover.get("percent_hard_avg_avg")
    macro_algae = percent_cover.get("percent_algae_avg_avg")
    return hard_coral, macro_algae


def get_benthic_averages(protocols_data, protocol):
    if protocol == QUADRAT_BENTHIC_PERCENT:
        return get_quadrat_benthic_percent_averages(protocols_data, protocol)

    percent_cover = (protocols_data.get(protocol) or {}).get(
        "percent_cover_benthic_category_avg"
    ) or {}
    hard_coral = percent_cover.get("Hard coral")
    macro_algae = percent_cover.get("Macroalgae")
    return hard_coral, macro_algae


def get_biomass_average(protocols_data):
    beltfish_data = protocols_data.get("beltfish") or {}
    return beltfish_data.get("biomass_kgha_avg")


def get_coral_reef_health(project_id, start_date, end_date):
    obj = RestrictedProjectSummarySampleEvent.objects.get_or_none(project_id=project_id)
    recs = obj.records if obj else []

    benthic_protocols = [
        BENTHIC_LIT,
        BENTHIC_PIT,
        BENTHIC_PQT,
        QUADRAT_BENTHIC_PERCENT,
    ]

    avg_vals = {
        "hard_coral_avgs": [],
        "macro_algae_avgs": [],
        "fish_biomass_avgs": [],
    }
    for rec in recs:
        sample_date_str = rec.get("sample_date")

        if sample_date_str is None:
            continue

        sample_date = datetime.strptime(rec.get("sample_date"), "%Y-%m-%d").date()
        if sample_date < start_date or sample_date > end_date:
            continue

        for benthic_protocol in benthic_protocols:
            protocols = rec.get("protocols") or {}
            hard_coral, macro_algae = get_benthic_averages(protocols, benthic_protocol)
            if hard_coral is not None:
                avg_vals["hard_coral_avgs"].append(hard_coral)
            if macro_algae is not None:
                avg_vals["macro_algae_avgs"].append(macro_algae)

        biomass = get_biomass_average(rec.get("protocols") or {})
        if biomass is not None:
            avg_vals["fish_biomass_avgs"].append(biomass)

    hard_coral_median = None
    macro_algae_median = None
    biomass_median = None

    if avg_vals["hard_coral_avgs"]:
        hard_coral_median = statistics.median(avg_vals["hard_coral_avgs"])
    if avg_vals["macro_algae_avgs"]:
        macro_algae_median = statistics.median(avg_vals["macro_algae_avgs"])
    if avg_vals["fish_biomass_avgs"]:
        biomass_median = statistics.median(avg_vals["fish_biomass_avgs"])

    return hard_coral_median, macro_algae_median, biomass_median


def create_id():
    return str(uuid.uuid4())


class GFCRRevenueSerializer(BaseAPISerializer):
    class Meta:
        model = GFCRRevenue
        exclude = []


class GFCRInvestmentSourceSerializer(BaseAPISerializer):
    class Meta:
        model = GFCRInvestmentSource
        exclude = []


class GFCRFinanceSolutionSerializer(BaseAPISerializer):
    investment_sources = GFCRInvestmentSourceSerializer(many=True, default=list, read_only=True)
    revenues = GFCRRevenueSerializer(many=True, default=list, read_only=True)

    class Meta:
        model = GFCRFinanceSolution
        exclude = []


class GFCRIndicatorSetSerializer(BaseAPISerializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cached_profiles = {}

    finance_solutions = GFCRFinanceSolutionSerializer(many=True, default=list, read_only=True)
    f4_1_calc = serializers.ReadOnlyField()
    f4_2_calc = serializers.ReadOnlyField()
    f4_3_calc = serializers.ReadOnlyField()
    suggested_citation = serializers.SerializerMethodField()

    class Meta:
        model = GFCRIndicatorSet
        exclude = []

    def _single_digit_precision(self, value):
        return round(value, 1) if isinstance(value, (int, float)) else None

    def _get_profiles(self, obj):
        project_id = str(obj.id)
        if project_id not in self._cached_profiles or self._cached_profiles[project_id] is None:
            self._cached_profiles[project_id] = get_profiles(obj)
        return self._cached_profiles[project_id]

    def get_citation_retrieved_text(self, obj):
        return citation_retrieved_text(obj.project.name)

    def get_default_citation(self, obj):
        project = obj.project
        profiles = self._get_profiles(project)
        return default_citation(project, profiles)

    def get_suggested_citation(self, obj):
        project = obj.project
        profiles = self._get_profiles(project)
        return f"{suggested_citation(project, profiles)} {citation_retrieved_text(project.name)}"

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        hard_coral_median, macro_algae_median, biomass_median = get_coral_reef_health(
            instance.project_id, instance.f4_start_date, instance.f4_end_date
        )
        ret["f4_1_calc"] = self._single_digit_precision(hard_coral_median)
        ret["f4_2_calc"] = self._single_digit_precision(macro_algae_median)
        ret["f4_3_calc"] = self._single_digit_precision(biomass_median)

        return ret


class IndicatorSetViewSet(BaseProjectApiViewSet):
    serializer_class = GFCRIndicatorSetSerializer
    project_lookup = "project"
    permission_classes = [Or(ProjectDataAdminPermission, AuthenticatedReadOnlyPermission)]

    def get_queryset(self):
        project_id = self.kwargs.get("project_pk")
        if project_id is None:
            return GFCRIndicatorSet.objects.none()
        return GFCRIndicatorSet.objects.filter(project_id=project_id, project__includes_gfcr=True)

    def _save_data(self, record, serializer, request, instance=None):
        kwargs = {
            "data": record,
            "context": {"request": request},
        }
        if instance:
            kwargs["instance"] = instance
        serializer_instance = serializer(**kwargs)
        serializer_instance.is_valid(raise_exception=True)
        return serializer_instance.save()

    def _delete_stale_nested_data(self, fk_field_name, fk_id, nested_model, nested_data):
        if fk_id:
            filter_args = {fk_field_name: fk_id}
            existing = {str(fs.pk): fs for fs in nested_model.objects.filter(**filter_args)}
            submitted = {fs_record["id"] for fs_record in nested_data if "id" in fs_record}

            for fs_id in existing:
                if fs_id not in submitted:
                    existing[fs_id].delete()

    def _pop_nested_data(self, record, nested_data_key):
        return record.pop(nested_data_key) if nested_data_key in record else []

    @transaction.atomic
    def _save(self, request, project_pk, pk=None, *args, **kwargs):
        project = Project.objects.get_or_none(pk=project_pk)
        if project.includes_gfcr is False:
            raise ValidationError(
                f"GFCR reporting for project {project.id}: {project.name} has not been enabled."
            )
        elif project_pk is None or project is None:
            return Response(status=status.HTTP_404_NOT_FOUND)

        queryset = self.get_queryset()
        if pk:
            try:
                indicator_set = queryset.get(pk=pk)
            except GFCRIndicatorSet.DoesNotExist:
                return Response(status=status.HTTP_404_NOT_FOUND)
        else:
            indicator_set = None

        data = request.data
        data["project"] = project_pk
        finance_solutions_data = self._pop_nested_data(data, "finance_solutions")

        # Save the indicator set
        indicator_set = self._save_data(
            request.data, self.serializer_class, request, instance=indicator_set
        )

        if pk:
            # Delete stale finance solutions
            self._delete_stale_nested_data(
                "indicator_set", pk, GFCRFinanceSolution, finance_solutions_data
            )

        # Save finance solutions
        for fs_record in finance_solutions_data:
            investment_sources_data = self._pop_nested_data(fs_record, "investment_sources")
            revenues_data = self._pop_nested_data(fs_record, "revenues")

            fs_record["indicator_set"] = indicator_set.pk
            if "id" in fs_record:
                fs_instance = GFCRFinanceSolution.objects.get_or_none(
                    id=fs_record["id"], indicator_set__project=project_pk
                )
            else:
                fs_instance = None

            if fs_instance:
                # Delete stale investment sources
                self._delete_stale_nested_data(
                    "finance_solution",
                    str(fs_instance.pk),
                    GFCRInvestmentSource,
                    investment_sources_data,
                )

                # Delete stale revenues
                self._delete_stale_nested_data(
                    "finance_solution", str(fs_instance.pk), GFCRRevenue, revenues_data
                )

            fin_sol_record = self._save_data(
                fs_record, GFCRFinanceSolutionSerializer, request, instance=fs_instance
            )

            # Save investment sources
            for investment_source_record in investment_sources_data:
                investment_source_record["finance_solution"] = fin_sol_record.pk
                if "id" in investment_source_record:
                    inv_src_instance = GFCRInvestmentSource.objects.get_or_none(
                        id=investment_source_record["id"],
                        finance_solution__indicator_set__project=project_pk,
                    )
                else:
                    inv_src_instance = None

                self._save_data(
                    investment_source_record,
                    GFCRInvestmentSourceSerializer,
                    request,
                    instance=inv_src_instance,
                )

            # Save revenues
            for revenue_record in revenues_data:
                revenue_record["finance_solution"] = fin_sol_record.pk
                if "id" in revenue_record:
                    rev_instance = GFCRRevenue.objects.get_or_none(
                        id=revenue_record["id"], finance_solution__indicator_set__project=project_pk
                    )
                else:
                    rev_instance = None

                self._save_data(
                    revenue_record, GFCRRevenueSerializer, request, instance=rev_instance
                )

        output_serializer = self.get_serializer(instance=indicator_set)
        return output_serializer.data

    def create(self, request, project_pk, *args, **kwargs):
        data = self._save(request, project_pk)
        return Response(data, status=status.HTTP_201_CREATED)

    def update(self, request, project_pk, pk=None, *args, **kwargs):
        data = self._save(request, project_pk, pk)
        return Response(data, status=status.HTTP_200_OK)
