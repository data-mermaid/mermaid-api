import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from rest_framework import exceptions
from rest_framework.authentication import BaseAuthentication

from api.models.base import Application, AuthUser, Profile
from api.utils import get_or_create_safeish
from api.utils.auth0utils import decode, get_jwt_token, get_user_info, is_hs_token

logger = logging.getLogger(__name__)


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
        return '{0} realm="{1}"'.format("Bearer", self.www_authenticate_realm)

    def authenticate(self, request):
        """
        Returns a two-tuple of `User` and token if a valid signature has been
        supplied using JWT-based authentication.  Otherwise returns `None`.
        """
        jwt_token = get_jwt_token(request)
        if jwt_token is None or is_hs_token(jwt_token) is False:
            logger.debug("Invalid Token: {}".format(jwt_token))
            return None

        payload = decode(jwt_token)
        profile = self._authenticate_profile(payload)

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
            msg = (
                "Invalid claim. sub should contain '|' or" + " '@clients': {}"
            ).format(sub)
            logger.debug(msg)
            raise exceptions.AuthenticationFailed(msg)

        return profile

    def _validate_profile(self, payload):
        """
        Returns an active Profile that matches the claims's user_id.
        """

        user_id = payload.get("sub")
        try:
            auth_user = AuthUser.objects.get(user_id=user_id)
            profile = auth_user.profile
        except AuthUser.DoesNotExist:
            user_info = get_user_info(user_id)
            profile, is_new = get_or_create_safeish(Profile, email=user_info["email"])

            if is_new is True:
                profile.first_name = user_info["first_name"]
                profile.last_name = user_info["last_name"]
                profile.save()

                if (
                    settings.MC_API_KEY is not None
                    and settings.MC_USER is not None
                    and settings.MC_LIST_ID is not None
                ):
                    from mailchimp3 import MailChimp

                    # https://developer.mailchimp.com/documentation/mailchimp/guides/manage-subscribers-with-the
                    # -mailchimp-api/
                    try:
                        client = MailChimp(
                            mc_api=settings.MC_API_KEY, mc_user=settings.MC_USER
                        )
                        client.lists.members.create(
                            settings.MC_LIST_ID,
                            {
                                "email_address": profile.email,
                                "status": "pending",
                                "merge_fields": {
                                    "FNAME": profile.first_name,
                                    "LNAME": profile.last_name,
                                },
                            },
                        )
                    except:  # Don't ever fail because subscription didn't work
                        logger.error(
                            "Unable to create mailchimp member {} {} <{}>".format(
                                profile.first_name, profile.last_name, profile.email
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


class AnonymousJWTAuthentication(JWTAuthentication):
    """
    If token has been passed it, JWT Authentication is used
    else user is Anonymous
    """

    def authenticate_header(self, request):
        pass

    def authenticate(self, request, *args, **kwargs):
        jwt_token = None
        try:
            jwt_token = get_jwt_token(request)
        except exceptions.AuthenticationFailed:
            pass

        if jwt_token:
            return super().authenticate(request, *args, **kwargs)
        return AnonymousUser(), None
