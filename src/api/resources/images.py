from django.db.models import Q, Subquery
from rest_framework import permissions
from rest_framework.exceptions import MethodNotAllowed

from ..models import Image, ObsBenthicPhotoQuadrat, ProjectProfile
from .base import BaseApiViewSet
from .classification.image import ImageSerializer


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
            for obs in obj.obs_benthic_photo_quadrats.all():
                project_id = getattr(obs, ObsBenthicPhotoQuadrat.project_lookup.split("__")[0]).id
                if ProjectProfile.objects.filter(profile=profile, project_id=project_id).exists():
                    return True

        return False


# class AllImagesFilterSet(BaseAPIFilterSet):
#     """
#     FilterSet for all images accessible to the user.
#     """
#     class Meta:
#         model = Image
#         fields = [
#             "created_on",
#             "updated_on",
#         ]


class AllImagesViewSet(BaseApiViewSet):
    serializer_class = ImageSerializer
    permission_classes = [permissions.IsAuthenticated, AllImagesPermission]
    # filterset_class = AllImagesFilterSetkj

    def get_queryset(self):
        qs = (
            Image.objects.prefetch_related("points", "points__annotations", "statuses")
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
