from django.db.models import Q
from rest_framework.viewsets import ReadOnlyModelViewSet

from ..models import (
    Project,
    ProjectProfile,
    RestrictedProjectSummarySampleEvent,
    UnrestrictedProjectSummarySampleEvent,
)
from ..permissions import UnauthenticatedReadOnlyPermission
from .base import ExtendedSerializer, StandardResultPagination


class ProjectSummarySampleEventSerializer(ExtendedSerializer):
    class Meta:
        model = UnrestrictedProjectSummarySampleEvent
        exclude = []


class ProjectSummarySampleEventViewSet(ReadOnlyModelViewSet):
    serializer_class = ProjectSummarySampleEventSerializer
    permission_classes = [UnauthenticatedReadOnlyPermission]
    authentication_classes = []
    pagination_class = StandardResultPagination

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
                ~Q(project_id__in=non_test_project_ids) & Q(project_id__in=project_ids)
            )
            unrestricted_qs = UnrestrictedProjectSummarySampleEvent.objects.filter(
                Q(project_id__in=non_test_project_ids) | ~Q(project_id__in=project_ids)
            )
            qs = restricted_qs.union(unrestricted_qs)
        else:
            qs = UnrestrictedProjectSummarySampleEvent.objects.filter(
                Q(project_id__in=non_test_project_ids)
            )

        return qs
