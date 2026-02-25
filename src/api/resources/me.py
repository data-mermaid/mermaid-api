from django.contrib.gis.db.models import Extent
from django.db.models import Count, Q
from rest_framework import permissions, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response

from api.auth0_management import Auth0DatabaseAuthenticationAPI, Auth0Users
from tools.models import MERMAIDFeature, UserMERMAIDFeature
from ..models import Profile, ProjectProfile
from ..utils import get_extent
from .base import BaseAPISerializer


class MeSerializer(BaseAPISerializer):
    picture = serializers.ReadOnlyField(source="picture_url")
    projects_bbox = serializers.SerializerMethodField()
    projects = serializers.SerializerMethodField()
    optional_features = serializers.SerializerMethodField()
    collect_state = serializers.JSONField(required=False)
    explore_state = serializers.JSONField(required=False)

    class Meta:
        model = Profile
        fields = [
            "id",
            "first_name",
            "last_name",
            "full_name",
            "email",
            "created_on",
            "updated_on",
            "picture",
            "projects_bbox",
            "projects",
            "optional_features",
            "collect_state",
            "explore_state",
        ]
        read_only_fields = ["id", "created_on", "updated_on", "full_name"]

    def get_queryset(self, o):
        if not hasattr(self, "_projects_cache"):
            self._projects_cache = (
                ProjectProfile.objects.select_related("project")
                .annotate(
                    num_active_sample_units=Count(
                        "project__collect_records",
                        filter=Q(project__collect_records__profile=o),
                        distinct=True,
                    ),
                    extent=Extent("project__sites__location"),
                )
                .filter(profile=o)
            )
        return self._projects_cache

    def get_projects(self, o):
        project_profiles = self.get_queryset(o)

        return [
            {
                "id": pp.project_id,
                "name": pp.project.name,
                "role": pp.role,
                "num_active_sample_units": pp.num_active_sample_units,
            }
            for pp in project_profiles
        ]

    def get_projects_bbox(self, o):
        extents = [pp.extent for pp in self.get_queryset(o) if pp.extent]
        if not extents:
            return None
        xmin = min(e[0] for e in extents)
        ymin = min(e[1] for e in extents)
        xmax = max(e[2] for e in extents)
        ymax = max(e[3] for e in extents)
        extent = (xmin, ymin, xmax, ymax)
        return get_extent(extent)

    def get_optional_features(self, profile):
        all_features = MERMAIDFeature.objects.all()
        user_features = {
            uf.feature_id: uf for uf in UserMERMAIDFeature.objects.filter(profile=profile)
        }

        result = []
        for feature in all_features:
            user_feature = user_features.get(feature.id)
            enabled = (
                user_feature.enabled if user_feature and user_feature.enabled else feature.enabled
            )

            result.append(
                {
                    "id": feature.id,
                    "label": feature.label,
                    "name": feature.name,
                    "enabled": enabled,
                }
            )

        return result


class AuthenticatedMePermission(permissions.BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return user.is_authenticated


class MeViewSet(viewsets.ModelViewSet):
    serializer_class = MeSerializer
    permission_classes = [
        AuthenticatedMePermission,
    ]

    def get_queryset(self):
        pass

    def list(self, request, *args, **kwargs):
        user = self.request.user
        profile = user.profile
        if profile is None:
            raise NotFound()

        return Response(self.serializer_class(profile).data)

    def _get_profile(self, request):
        user = request.user
        profile = user.profile
        if profile is None:
            raise NotFound()
        return profile

    def _sync_auth0_metadata(self, profile, email, first_name, last_name):
        auth_user_ids = [au.user_id for au in profile.authusers.all()]
        auth_users_client = Auth0Users()

        for user_id in auth_user_ids:
            auth_users_client.update(
                {
                    "user_id": user_id,
                    "user_metadata": {
                        "first_name": first_name,
                        "last_name": last_name,
                        "email": email,
                    },
                }
            )

    def _update_profile(self, request, partial=False):
        # Used for updating a user's own profile details
        profile = self._get_profile(request)

        me_serializer = MeSerializer(
            instance=profile, data=request.data, partial=partial, context={"request": request}
        )
        if not me_serializer.is_valid():
            raise ValidationError(me_serializer.errors)

        if any(k in request.data for k in ["email", "first_name", "last_name"]):
            validated = me_serializer.validated_data
            email = validated["email"] if "email" in validated else profile.email
            first_name = (
                validated["first_name"] if "first_name" in validated else profile.first_name
            )
            last_name = validated["last_name"] if "last_name" in validated else profile.last_name
            self._sync_auth0_metadata(profile, email, first_name, last_name)

        me_serializer.save()
        return Response(me_serializer.data)

    def put(self, request, *args, **kwargs):
        return self._update_profile(request, partial=False)

    def patch(self, request, *args, **kwargs):
        return self._update_profile(request, partial=True)

    def _get_email(self, profile):
        auth_user_ids = [au.user_id for au in profile.authusers.all()]
        auth_users_client = Auth0Users()
        for user_id in auth_user_ids:
            user_info = auth_users_client.get_user(user_id)
            for identity in user_info.get("identities") or []:
                provider = identity.get("connection")
                if provider != Auth0DatabaseAuthenticationAPI.CONNECTION:
                    continue
                return user_info.get("email")
        return None

    @action(detail=False, methods=["post"])
    def change_password(self, request, *args, **kwargs):
        user = self.request.user
        profile = user.profile
        if profile is None:
            raise NotFound()

        email = self._get_email(profile)
        if email is None:
            raise ValidationError("Unable to change password from 3rd party user accounts")

        auth = Auth0DatabaseAuthenticationAPI()
        return Response(auth.change_password(email))
