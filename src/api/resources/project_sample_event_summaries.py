from django.db.models import CharField, Q
from django_filters import BaseInFilter, CharFilter
from rest_framework.serializers import SerializerMethodField
from rest_framework.viewsets import ReadOnlyModelViewSet
from rest_framework_gis.filters import GeoFilterSet

from ..auth_backends import AnonymousJWTAuthentication
from ..models import (
    Project,
    ProjectProfile,
    RestrictedProjectSummarySampleEvent,
    UnrestrictedProjectSummarySampleEvent,
)
from ..models.summary_sample_events import BaseProjectSummarySampleEvent
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
        model = UnrestrictedProjectSummarySampleEvent
        exclude = []


class ProjectSummarySampleEventFilterSet(OrFilterSetMixin, GeoFilterSet):
    project_id = BaseInFilter(method="id_lookup")
    project_name = BaseInFilter(method="char_lookup")
    project_admins = BaseInFilter(method="json_name_lookup")

    class Meta:
        model = BaseProjectSummarySampleEvent
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
            }
        }


class ProjectSummarySampleEventViewSet(ReadOnlyModelViewSet):
    serializer_class = ProjectSummarySampleEventSerializer
    permission_classes = [UnauthenticatedReadOnlyPermission]
    authentication_classes = [AnonymousJWTAuthentication]
    pagination_class = StandardResultPagination
    filterset_class = ProjectSummarySampleEventFilterSet

    def get_queryset(self):
        user = self.request.user
        if hasattr(user, "profile"):
            profile = user.profile
        else:
            profile = None

        non_test_project_ids = Project.objects.filter(~Q(status=Project.TEST)).values_list(
            "id", flat=True
        )
        if profile:
            project_ids = (
                ProjectProfile.objects.filter(profile=profile)
                .values_list("project_id", flat=True)
                .distinct()
            )
            restricted_qs = RestrictedProjectSummarySampleEvent.objects.filter(
                Q(project_id__in=non_test_project_ids) & Q(project_id__in=project_ids)
            )
            unrestricted_qs = UnrestrictedProjectSummarySampleEvent.objects.filter(
                Q(project_id__in=non_test_project_ids) & ~Q(project_id__in=project_ids)
            )
            qs = restricted_qs.union(unrestricted_qs)
        else:
            qs = UnrestrictedProjectSummarySampleEvent.objects.filter(
                Q(project_id__in=non_test_project_ids)
            )

        return qs.order_by("project_id")
