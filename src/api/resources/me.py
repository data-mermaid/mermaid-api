from django.contrib.gis.geos import MultiPoint
from django.db.models import Prefetch
from rest_framework import permissions, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response

from api.auth0_management import Auth0DatabaseAuthenticationAPI, Auth0Users
from tools.models import MERMAIDFeature, UserMERMAIDFeature
from ..models import Profile, ProjectProfile, Site
from .base import BaseAPISerializer


def calculate_bbox_centroid(site_locations):
    """Given a list of Point objects, return the center of the bounding box."""
    if not site_locations:
        return None

    multipoint = MultiPoint(site_locations)
    bbox = multipoint.envelope.extent  # [xmin, ymin, xmax, ymax]
    return {
        "lat": round((bbox[1] + bbox[3]) / 2, 3),
        "lng": round((bbox[0] + bbox[2]) / 2, 3),
    }


class MeSerializer(BaseAPISerializer):
    picture = serializers.ReadOnlyField(source="picture_url")
    projects_centroid_latlng = serializers.SerializerMethodField()
    projects = serializers.SerializerMethodField()
    optional_features = serializers.SerializerMethodField()

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
            "projects_centroid_latlng",
            "projects",
            "optional_features",
        ]

    def get_queryset(self, o):
        if not hasattr(self, "_project_profiles_cache"):
            self._project_profiles_cache = (
                ProjectProfile.objects.select_related("project")
                .prefetch_related(
                    Prefetch("project__sites", queryset=Site.objects.only("id", "location")),
                    "project__collect_records",
                )
                .filter(profile=o)
            )
        return self._project_profiles_cache

    def get_projects(self, o):
        qry = self.get_queryset(o)

        projects = []
        for pp in qry:
            site_locations = [site.location for site in pp.project.sites.all() if site.location]
            projects.append(
                {
                    "id": pp.project_id,
                    "name": pp.project.name,
                    "role": pp.role,
                    "num_active_sample_units": pp.project.collect_records.filter(
                        profile=pp.profile
                    ).count(),
                    "centroid_latlng": calculate_bbox_centroid(site_locations),
                }
            )

        return projects

    def get_projects_centroid_latlng(self, o):
        qry = self.get_queryset(o)

        all_site_locations = []
        for pp in qry:
            all_site_locations.extend(
                site.location for site in pp.project.sites.all() if site.location
            )

        return calculate_bbox_centroid(all_site_locations)

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

    def put(self, request, *args, **kwargs):
        """
        Used for updating a user's own profile details
        """
        user = self.request.user
        profile = user.profile
        if profile is None:
            raise NotFound()

        me_serializer = MeSerializer(
            data=request.data, instance=profile, context={"request": request}
        )

        if me_serializer.is_valid() is False:
            errors = {"Profile": me_serializer.errors}
            raise ValidationError(errors)

        auth_user_ids = [au.user_id for au in profile.authusers.all()]
        auth_users_client = Auth0Users()
        email = me_serializer.validated_data.get("email")
        first_name = me_serializer.validated_data.get("first_name")
        last_name = me_serializer.validated_data.get("last_name")

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
        me_serializer.save()
        return Response(me_serializer.validated_data)

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
