from django.db.models import OuterRef, Q, Subquery
from django_filters import rest_framework as filters

from ...exceptions import check_uuid
from ...models import ClassificationStatus, CollectRecord, ObsBenthicPhotoQuadrat
from ...permissions import ProjectDataAdminPermission, ProjectDataCollectorPermission
from ..base import BaseAPIFilterSet, BaseAPISerializer, BaseProjectApiViewSet


class ClassificationStatusSerializer(BaseAPISerializer):
    class Meta:
        model = ClassificationStatus
        fields = ["id", "image", "status", "message", "data"]


class ClassificationStatusFilterSet(BaseAPIFilterSet):
    collect_record = filters.BooleanFilter(field_name="collect_record_id", method="filter_covars")

    def filter_covars(self, queryset, name, value):
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

    def get_queryset(self):
        show_all = "showall" in self.request.query_params
        qs = ClassificationStatus.objects.all()

        if show_all is True:
            return qs

        latest_status_subquery = (
            ClassificationStatus.objects.filter(image=OuterRef("image"))
            .order_by("-created_on")
            .values("id")[:1]
        )

        return ClassificationStatus.objects.filter(id__in=Subquery(latest_status_subquery))

    def limit_to_project(self, request, *args, **kwargs):
        qs = self.get_queryset()
        project_pk = check_uuid(kwargs["project_pk"])
        cr_ids = CollectRecord.objects.filter(project_id=project_pk).values_list("id", flat=True)
        return qs.filter(
            Q(image__collect_record_id__in=cr_ids)
            | Q(
                **{
                    f"image__obs_benthic_photo_quadrats__{ObsBenthicPhotoQuadrat.project_lookup}": project_pk
                }
            )
        )
