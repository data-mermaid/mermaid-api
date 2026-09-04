"""Self-service management of a person's own API keys.

The Django admin issues keys for anyone and is a superuser tool. This resource
is the everyday path: a signed-in person lists, names, mints and revokes keys
that act as their own profile, and nobody else's. Scoping is by ownership, the
way `/notifications/` is: the queryset is filtered to `request.user.profile`,
so another person's key is a 404 rather than a 403.

The raw key appears exactly once, in the `key` field of the create response.
It is not stored, so it cannot be shown again; losing it means minting a new
key. Keys are revoked rather than deleted so the audit trail survives, which
is also why the resource has no DELETE.
"""

from django.utils import timezone
from django_filters import BooleanFilter
from rest_framework import serializers, status
from rest_framework.decorators import action
from rest_framework.response import Response

from ..models import APIKey
from ..permissions import APIKeyOwnerPermission
from ..utils.apikeys import default_expires_at
from .base import BaseAPIFilterSet, BaseAPISerializer, BaseApiViewSet

OWNER_REVOKED = "owner_revoked"


class APIKeySerializer(BaseAPISerializer):
    """What a person sees about one of their keys. Never the secret.

    `secret_hash` is left out on purpose: nothing a client does needs it, and a
    digest that never leaves the database cannot be compared against offline.
    `name` is the only writable field; the lifetime of a credential is fixed
    when it is minted, so `expires_at` cannot be pushed out afterwards.
    """

    status = serializers.SerializerMethodField()

    class Meta:
        model = APIKey
        fields = [
            "id",
            "name",
            "key_id",
            "status",
            "is_active",
            "expires_at",
            "last_used_at",
            "last_used_ip",
            "revoked_at",
            "revoked_reason",
            "created_on",
            "updated_on",
            "updated_by",
        ]
        read_only_fields = [
            "id",
            "key_id",
            "is_active",
            "expires_at",
            "last_used_at",
            "last_used_ip",
            "revoked_at",
            "revoked_reason",
            "created_on",
            "updated_on",
        ]

    def get_status(self, obj):
        """One word for why a key does or does not work right now."""

        if obj.revoked_at is not None:
            return "revoked"
        if obj.is_expired:
            return "expired"
        if not obj.is_active:
            return "inactive"
        return "active"


class APIKeyCreateSerializer(serializers.Serializer):
    """Input for minting a key. Output is `APIKeySerializer` plus `key`.

    Expiry mirrors the admin form: leave `expires_at` out and the key lives
    for the default lifetime; a key that never expires has to be asked for
    with `never_expires`, so that no-expiry is never the silent default.
    """

    name = serializers.CharField(max_length=APIKey._meta.get_field("name").max_length)
    expires_at = serializers.DateTimeField(required=False, allow_null=True)
    never_expires = serializers.BooleanField(required=False, default=False)

    def validate_expires_at(self, value):
        if value is not None and value <= timezone.now():
            raise serializers.ValidationError("expires_at must be in the future.")
        return value

    def validate(self, attrs):
        expires_at = attrs.get("expires_at")
        never_expires = attrs.get("never_expires", False)
        if never_expires and expires_at is not None:
            raise serializers.ValidationError(
                {"expires_at": "Set expires_at or never_expires, not both."}
            )
        if never_expires:
            attrs["expires_at"] = None
        elif expires_at is None:
            attrs["expires_at"] = default_expires_at()
        return attrs


class APIKeyFilterSet(BaseAPIFilterSet):
    # revoked=true is "has a revoked_at"; the isnull lookup is inverted so the
    # parameter reads the way a person would ask the question.
    revoked = BooleanFilter(field_name="revoked_at", lookup_expr="isnull", exclude=True)

    class Meta:
        model = APIKey
        fields = ["name", "is_active", "revoked"]


class APIKeyViewSet(BaseApiViewSet):
    serializer_class = APIKeySerializer
    model = APIKey
    filterset_class = APIKeyFilterSet
    permission_classes = [APIKeyOwnerPermission]
    search_fields = ["name", "key_id"]

    # No PUT: a whole-object replace has nothing to replace but the name, and
    # no DELETE: keys are revoked, not erased, so the audit trail stays.
    http_method_names = ["get", "head", "options", "post", "patch"]

    def get_queryset(self):
        profile = getattr(self.request.user, "profile", None)
        if profile is None:
            return APIKey.objects.none()
        return APIKey.objects.filter(profile=profile).order_by("-created_on")

    def get_serializer_class(self):
        if self.action == "create":
            return APIKeyCreateSerializer
        return super().get_serializer_class()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        profile = request.user.profile
        key, raw = APIKey.issue(
            profile=profile,
            name=serializer.validated_data["name"],
            expires_at=serializer.validated_data["expires_at"],
            actor=request.user.get_username(),
            created_by=profile,
        )

        # The one and only time the secret is readable.
        data = APIKeySerializer(key, context=self.get_serializer_context()).data
        data["key"] = raw
        headers = self.get_success_headers(data)
        return Response(data, status=status.HTTP_201_CREATED, headers=headers)

    @action(detail=True, methods=["post"])
    def revoke(self, request, pk=None):
        """Retire one of the caller's keys. Idempotent: re-revoking is a no-op."""

        key = self.get_object()
        actor = request.user.get_username()
        key.revoke(f"{OWNER_REVOKED}:{actor}"[:255], actor=actor)
        return Response(self.get_serializer(key).data)
