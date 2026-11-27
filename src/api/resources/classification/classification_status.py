from django.db.models import OuterRef, Q, Subquery
from django_filters import rest_framework as filters
from rest_framework.exceptions import MethodNotAllowed

from ...exceptions import check_uuid
from ...models import ClassificationStatus, CollectRecord, ObsBenthicPhotoQuadrat
from ...permissions import ProjectDataAdminPermission, ProjectDataCollectorPermission
from ..base import BaseAPIFilterSet, BaseAPISerializer, BaseProjectApiViewSet


class ClassificationStatusSerializer(BaseAPISerializer):
    class Meta:
        model = ClassificationStatus
        fields = ["id", "image", "status", "message", "data"]


class ClassificationStatusFilterSet(BaseAPIFilterSet):
    collect_record = filters.CharFilter(
        field_name="collect_record_id", method="filter_collect_record"
    )

    def filter_collect_record(self, queryset, name, value):
        return queryset.filter(image__collect_record_id=value)

    class Meta:
        model = ClassificationStatus
        fields = ["collect_record", "image", "status"]


class ClassificationStatusViewSet(BaseProjectApiViewSet):
    queryset = ClassificationStatus.objects.all()
    serializer_class = ClassificationStatusSerializer
    filterset_class = ClassificationStatusFilterSet

    permission_classes = [
        ProjectDataCollectorPermission,
        ProjectDataAdminPermission,
    ]

    def _project_scoped_queryset(self, project_pk):
        # Statuses whose image belongs to this project, via its collect records or its
        # submitted benthic-photo-quadrat observations.
        cr_ids = CollectRecord.objects.filter(project_id=project_pk).values_list("id", flat=True)
        return ClassificationStatus.objects.filter(
            Q(image__collect_record_id__in=cr_ids)
            | Q(
                **{
                    f"image__obs_benthic_photo_quadrats__{ObsBenthicPhotoQuadrat.project_lookup}": project_pk
                }
            )
        ).distinct()

    def get_queryset(self):
        # Scope to the URL project here, not only in limit_to_project: get_queryset was
        # returning the whole table (and the entire table for ?showall), leaking other
        # projects' classification statuses (card 2290/2231).
        project_pk = self.kwargs.get("project_pk")
        if project_pk is None:
            return ClassificationStatus.objects.none()
        qs = self._project_scoped_queryset(check_uuid(project_pk))

        if "showall" in self.request.query_params:
            return qs.order_by("-created_on")

        latest_status_subquery = (
            ClassificationStatus.objects.filter(image=OuterRef("image"))
            .order_by("-created_on")
            .values("id")[:1]
        )
        return qs.filter(id__in=Subquery(latest_status_subquery)).order_by("-created_on")

    def create(self, request, **kwargs):
        raise MethodNotAllowed("POST")

    def update(self, request, pk=None, **kwargs):
        raise MethodNotAllowed("PUT")

    def partial_update(self, request, pk=None, **kwargs):
        raise MethodNotAllowed("PATCH")

    def destroy(self, request, pk=None, **kwargs):
        raise MethodNotAllowed("DELETE")
