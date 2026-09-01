import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.core.cache import cache
from django.utils import timezone
from django.utils.encoding import smart_str
from rest_framework import exceptions
from rest_framework.authentication import BaseAuthentication, get_authorization_header

from api.models.base import APIKey, Application, AuthUser, Profile
from api.utils import get_or_create_safeish
from api.utils.apikeys import get_environment_label, parse_api_key, secret_matches
from api.utils.auth0utils import decode, get_jwt_token, get_user_info, is_hs_token

logger = logging.getLogger(__name__)


def _get_client_ip(request):
    xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
    return xff.split(",")[0].strip() if xff else request.META.get("REMOTE_ADDR", "unknown")


class JWTAuthentication(BaseAuthentication):
    """
    Token based authentication using the JSON Web Token standard.
    """

    www_authenticate_realm = "api"

    def authenticate_header(self, request):
        """
        Return a string to be used as the value of the `WWW-Authenticate`
        header in a `401 Unauthenticated` response, or `None` if the
        authentication scheme should return `403 Permission Denied` responses.
        """
        return f'Bearer realm="{self.www_authenticate_realm}"'

    def authenticate(self, request):
        """
        Returns a two-tuple of `User` and token if a valid signature has been
        supplied using JWT-based authentication.  Otherwise returns `None`.
        """
        jwt_token = get_jwt_token(request)
        if jwt_token is None or is_hs_token(jwt_token) is False:
            logger.debug(f"Invalid Token: {jwt_token}")
            return None

        try:
            payload = decode(jwt_token)
            profile = self._authenticate_profile(payload)
        except (exceptions.AuthenticationFailed, exceptions.ValidationError) as exc:
            logger.warning(
                "[auth0.failed_auth] reason=%s ip=%s path=%s",
                str(exc),
                _get_client_ip(request),
                request.path,
            )
            raise

        # use a dummy Django user. (it doesn't stop you from scaling
        # to any number of instances as well).
        user = get_user_model()(username=payload.get("sub"), password="auth0")
        user.profile = profile
        return (user, jwt_token)

    def _authenticate_profile(self, payload):
        sub = payload.get("sub")
        if not sub:
            msg = "Missing 'sub' claim."
            logger.debug(msg)
            raise exceptions.AuthenticationFailed(msg)

        if "@clients" in sub:
            client_id = sub.split("@clients")[0]
            app = self._validate_app(client_id)
            profile = app.profile

        elif "|" in sub:
            profile = self._validate_profile(payload)

        else:
            msg = ("Invalid claim. sub should contain '|' or" + " '@clients': {}").format(sub)
            logger.debug(msg)
            raise exceptions.AuthenticationFailed(msg)

        return profile

    def _validate_profile(self, payload):
        """
        Returns an active Profile that matches the claims's user_id.
        """
        SECS_PER_DAY = 86400
        user_id = payload.get("sub")
        now_datetime = timezone.now()
        try:
            auth_user = AuthUser.objects.get(user_id=user_id)
            profile = auth_user.profile

            if (now_datetime - profile.updated_on).total_seconds() > SECS_PER_DAY:
                # ponytail: cosmetic picture refresh — a transient Auth0 hiccup must
                # not 503 an already-authenticated user. Keep the cached profile.
                try:
                    user_info = get_user_info(user_id)
                    profile.picture_url = user_info["picture"]
                    profile.save()
                except exceptions.APIException:
                    # Bump updated_on so we don't re-enter (and re-fail) the refresh
                    # on every subsequent request while Auth0 is unavailable. Retry
                    # naturally on the next >24h window.
                    profile.save(update_fields=["updated_on"])
                    logger.warning(
                        "[auth0.refresh_skipped] picture refresh failed for %s; "
                        "serving cached profile",
                        user_id,
                    )
        except AuthUser.DoesNotExist:
            user_info = get_user_info(user_id)
            profile, is_new = get_or_create_safeish(Profile, email=user_info["email"])
            profile.first_name = user_info["first_name"]
            profile.last_name = user_info["last_name"]
            profile.picture_url = user_info["picture"]
            profile.save()

            if is_new is True:
                if (
                    settings.MC_API_KEY is not None
                    and settings.MC_USER is not None
                    and settings.MC_LIST_ID is not None
                ):
                    from mailchimp3 import MailChimp
                    from mailchimp3.helpers import get_subscriber_hash

                    # https://developer.mailchimp.com/documentation/mailchimp/guides/manage-subscribers-with-the
                    # -mailchimp-api/
                    try:
                        client = MailChimp(mc_api=settings.MC_API_KEY, mc_user=settings.MC_USER)

                        merge_fields = {"API": "yes"}
                        if profile.first_name and profile.first_name.strip():
                            merge_fields["FNAME"] = profile.first_name.strip()
                        if profile.last_name and profile.last_name.strip():
                            merge_fields["LNAME"] = profile.last_name.strip()

                        client.lists.members.create_or_update(
                            settings.MC_LIST_ID,
                            get_subscriber_hash(profile.email),
                            {
                                "email_address": profile.email,
                                "status_if_new": "subscribed",
                                "merge_fields": merge_fields,
                            },
                        )
                    except Exception as err:  # Don't ever fail because subscription didn't work
                        logger.error(
                            "Unable to create mailchimp member {} {} <{}>: {}".format(
                                profile.first_name, profile.last_name, profile.email, str(err)
                            )
                        )

        get_or_create_safeish(AuthUser, profile=profile, user_id=user_id)

        return profile

    def _validate_app(self, client_id):
        """
        Returns an active RegisteredApp that matches the claims's client_id.
        """

        try:
            app = Application.objects.get(client_id=client_id)
        except Application.DoesNotExist:
            msg = "Application does not exist: " + client_id
            logger.debug(msg)
            raise exceptions.PermissionDenied(msg)

        return app


def has_api_key_scheme(request):
    """True when the caller presented an `Authorization: ApiKey ...` header."""

    auth = get_authorization_header(request).split()
    if not auth:
        return False
    return smart_str(auth[0]).lower() == APIKeyAuthentication.keyword.lower()


class APIKeyAuthentication(BaseAuthentication):
    """
    Authentication for machine clients using a MERMAID-issued API key.

    The key is read from `Authorization: ApiKey mmd_<env>_<key_id>_<secret>`
    and never from the query string, which would put a long-lived credential
    into nginx, ALB and Sentry logs.

    A key that is present but bad always fails closed with a 401. Returning
    `None` would let a misconfigured client fall through to the anonymous
    backend and silently read public data instead of seeing the error.
    """

    keyword = "ApiKey"
    www_authenticate_realm = "api"
    # per-key throttle on the last_used_at write, in seconds
    last_used_throttle = 60

    def authenticate_header(self, request):
        return f'{self.keyword} realm="{self.www_authenticate_realm}"'

    def authenticate(self, request):
        auth = get_authorization_header(request).split()
        if not auth or smart_str(auth[0]).lower() != self.keyword.lower():
            # not our scheme; let the next backend try
            return None

        if len(auth) != 2:
            raise self._fail(request, "malformed_header", None)

        raw = smart_str(auth[1])
        try:
            env, key_id, secret = parse_api_key(raw)
        except ValueError:
            raise self._fail(request, "malformed_key", None)

        # ImproperlyConfigured here is a deployment error, not a client error;
        # let it surface as a 500. api.checks catches it at startup.
        if env != get_environment_label():
            raise self._fail(
                request,
                "wrong_environment",
                key_id,
                detail="key issued for a different environment",
            )

        try:
            api_key = APIKey.objects.select_related("profile").get(key_id=key_id)
        except APIKey.DoesNotExist:
            raise self._fail(request, "unknown_key_id", key_id)

        if not secret_matches(secret, api_key.secret_hash):
            raise self._fail(request, "bad_secret", key_id)

        if not api_key.is_active:
            raise self._fail(request, "inactive", key_id)
        if api_key.revoked_at is not None:
            raise self._fail(request, "revoked", key_id)
        if api_key.expires_at is not None and api_key.expires_at < timezone.now():
            raise self._fail(request, "expired", key_id)

        self._touch(api_key, _get_client_ip(request))

        # dummy Django user, as in JWTAuthentication
        user = get_user_model()(username=f"apikey|{api_key.key_id}", password="apikey")
        user.profile = api_key.profile
        return (user, api_key)

    def _fail(self, request, reason, key_id, detail=None):
        """Log the rejection and return the exception for the caller to raise."""

        logger.warning(
            "[apikey.failed_auth] reason=%s key_id=%s ip=%s path=%s",
            reason,
            key_id or "malformed",
            _get_client_ip(request),
            request.path,
        )
        # One opaque message: which check failed is not the caller's business,
        # and saying so would narrow a guessing attack.
        return exceptions.AuthenticationFailed(detail or "Invalid API key")

    def _touch(self, api_key, ip):
        """Record usage, at most once per key per throttle window.

        A busy client would otherwise write to the row on every request.
        """

        cache_key = f"apikey:last_used:{api_key.key_id}"
        if cache.get(cache_key):
            return
        cache.set(cache_key, True, self.last_used_throttle)
        now = timezone.now()
        # update() to avoid touching updated_on/updated_by on every call
        APIKey.objects.filter(pk=api_key.pk).update(last_used_at=now, last_used_ip=ip)
        api_key.last_used_at = now
        api_key.last_used_ip = ip


class AnonymousJWTAuthentication(JWTAuthentication):
    """
    If token has been provided, JWT Authentication is used
    else user is set to AnonymousUser
    """

    def authenticate(self, request, *args, **kwargs):
        # An API key on a public endpoint must be validated, not ignored:
        # a bad key has to 401 rather than quietly return public data.
        if has_api_key_scheme(request):
            return APIKeyAuthentication().authenticate(request)

        jwt_token = None
        try:
            jwt_token = get_jwt_token(request)
        except exceptions.AuthenticationFailed:
            pass

        if jwt_token:
            return super().authenticate(request)
        return AnonymousUser(), None
