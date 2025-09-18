from django.db.models import CharField, JSONField, Q, Subquery
from django_filters import BaseInFilter, CharFilter
from rest_framework.serializers import SerializerMethodField
from rest_framework.viewsets import ReadOnlyModelViewSet
from rest_framework_gis.filters import GeoFilterSet

from ..auth_backends import AnonymousJWTAuthentication
from ..models import Project, ProjectProfile
from ..models.summary_sample_events import ProjectSummarySampleEventView
from ..permissions import UnauthenticatedReadOnlyPermission
from ..utils.project import citation_retrieved_text
from .base import ExtendedSerializer, StandardResultPagination
from .mixins import OrFilterSetMixin


class ProjectSummarySampleEventSerializer(ExtendedSerializer):
    suggested_citation = SerializerMethodField()
    records = SerializerMethodField()

    def get_suggested_citation(self, obj):
        suggested_citation = ""
        if obj.suggested_citation != "":
            suggested_citation = f"{obj.suggested_citation} "
        return f"{suggested_citation}{citation_retrieved_text(obj.project_name)}"

    def get_records(self, obj):
        for se in obj.records:
            if "suggested_citation" not in se:
                se["suggested_citation"] = ""
            se["suggested_citation"] += f' {citation_retrieved_text(se["project_name"])}'
        return obj.records

    class Meta:
        model = ProjectSummarySampleEventView
        exclude = []


class ProjectSummarySampleEventFilterSet(OrFilterSetMixin, GeoFilterSet):
    project_id = BaseInFilter(method="id_lookup")
    project_name = BaseInFilter(method="char_lookup")
    project_admins = BaseInFilter(method="json_name_lookup")
    country_name = BaseInFilter(method="records_lookup")
    site_id = BaseInFilter(method="records_lookup")
    site_name = BaseInFilter(method="records_lookup")
    country_id = BaseInFilter(method="records_lookup")
    country_name = BaseInFilter(method="records_lookup")
    tag_id = BaseInFilter(field_name="tags", method="records_lookup")
    tag_name = BaseInFilter(field_name="tags", method="records_lookup")
    management_id = BaseInFilter(method="records_lookup")
    management_name = BaseInFilter(method="records_lookup")

    def records_lookup(self, queryset, name, value):
        q = Q()
        for v in set(value):
            if v is not None and v != "":
                q |= Q(**{"records__contains": [{name: str(v).strip()}]})
        return queryset.filter(q).distinct()

    class Meta:
        model = ProjectSummarySampleEventView
        fields = [
            "project_id",
            "project_name",
            "project_admins",
            "data_policy_beltfish",
            "data_policy_benthiclit",
            "data_policy_benthicpit",
            "data_policy_habitatcomplexity",
            "data_policy_bleachingqc",
            "data_policy_benthicpqt",
        ]

        filter_overrides = {
            CharField: {
                "filter_class": CharFilter,
                "extra": lambda f: {"lookup_expr": "icontains"},
            },
            JSONField: {
                "filter_class": CharFilter,
                "extra": lambda f: {"lookup_expr": "icontains"},
            },
        }


class ProjectSummarySampleEventViewSet(ReadOnlyModelViewSet):
    serializer_class = ProjectSummarySampleEventSerializer
    permission_classes = [UnauthenticatedReadOnlyPermission]
    authentication_classes = [AnonymousJWTAuthentication]
    pagination_class = StandardResultPagination
    filterset_class = ProjectSummarySampleEventFilterSet
    queryset = ProjectSummarySampleEventView.objects.all().order_by("project_id")

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        profile = getattr(user, "profile", None)

        non_test_projects = Project.objects.exclude(status=Project.TEST).values("id")
        qs = qs.filter(project_id__in=Subquery(non_test_projects))

        if profile:
            proj_ids = ProjectProfile.objects.filter(profile=profile).values("project_id")
            qs = qs.filter(
                ~Q(project_id__in=Subquery(proj_ids)) & Q(access="unrestricted")
                | Q(access="restricted") & Q(project_id__in=Subquery(proj_ids))
            )
            print(qs.query)
            return qs
        else:
            return qs.filter(access="unrestricted")
