from django.db.models import Q, Subquery
from django_filters import CharFilter
from rest_framework import permissions, serializers
from rest_framework.exceptions import MethodNotAllowed

from ..models import Image, ObsBenthicPhotoQuadrat, ProjectProfile
from .base import BaseAPIFilterSet, BaseApiViewSet
from .classification.image import ImageSerializer


class ImageExtSerializer(ImageSerializer):
    project_id = serializers.SerializerMethodField()
    project_name = serializers.SerializerMethodField()

    def get_project_id(self, obj):
        return obj.project.id

    def get_project_name(self, obj):
        return obj.project.name


class AllImagesPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        profile = getattr(request.user, "profile", None)
        if profile is None:
            return False

        return request.method in permissions.SAFE_METHODS

    def has_object_permission(self, request, view, obj):
        profile = getattr(request.user, "profile", None)
        if profile is None:
            return False

        if hasattr(obj, "obs_benthic_photo_quadrats"):
            if ProjectProfile.objects.filter(profile=profile, project=obj.project).exists():
                return True

        return False


class AllImagesFilterSet(BaseAPIFilterSet):
    project_id = CharFilter(
        field_name="obs_benthic_photo_quadrats__benthic_photo_quadrat_transect__quadrat_transect__sample_event__site__project__id",
        lookup_expr="iexact",
    )
    project_name = CharFilter(
        field_name="obs_benthic_photo_quadrats__benthic_photo_quadrat_transect__quadrat_transect__sample_event__site__project__name",
        lookup_expr="iexact",
    )

    class Meta:
        model = Image
        fields = [
            "project_id",
            "project_name",
        ]


class AllImagesViewSet(BaseApiViewSet):
    serializer_class = ImageExtSerializer
    permission_classes = [permissions.IsAuthenticated, AllImagesPermission]
    filterset_class = AllImagesFilterSet

    def get_queryset(self):
        qs = (
            Image.objects.prefetch_related(
                "points",
                "points__annotations",
                "statuses",
                (
                    "obs_benthic_photo_quadrats__benthic_photo_"
                    "quadrat_transect__quadrat_transect__sample_event__site__project"
                ),
            )
            .all()
            .order_by("-created_on")
        )

        profile = getattr(self.request.user, "profile", None)
        if profile is None:
            return qs.none()

        user_project_ids = ProjectProfile.objects.filter(profile=profile).values("project_id")

        return qs.filter(
            Q(
                **{
                    f"obs_benthic_photo_quadrats__{ObsBenthicPhotoQuadrat.project_lookup}__in": Subquery(
                        user_project_ids
                    )
                }
            )
        ).distinct()

    def create(self, request, *args, **kwargs):
        raise MethodNotAllowed("POST")

    def update(self, request, *args, **kwargs):
        raise MethodNotAllowed("PUT")

    def partial_update(self, request, *args, **kwargs):
        raise MethodNotAllowed("PATCH")

    def destroy(self, request, *args, **kwargs):
        raise MethodNotAllowed("DELETE")
