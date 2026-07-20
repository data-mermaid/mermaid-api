import json
import logging
import secrets
import string
from urllib.request import urlopen

from auth0.authentication import GetToken
from auth0.authentication.exceptions import Auth0Error
from auth0.management import ManagementClient
from auth0.management.core.api_error import ApiError
from django.utils.encoding import smart_str
from django.utils.translation import gettext as _
from jose import jws, jwt
from requests.exceptions import ConnectionError, ReadTimeout, Timeout
from rest_framework import exceptions
from rest_framework.authentication import get_authorization_header

from api.exceptions import Auth0ServiceUnavailable
from api.models import Application, AuthUser
from app import settings

logger = logging.getLogger(__name__)


class Auth0ClientManager(object):
    _chars = string.ascii_letters + string.digits
    _secret_len = 48

    def __init__(self, domain, token):
        self.domain = domain
        self.token = token
        self.auth0 = ManagementClient(domain=domain, token=token)

    def delete_client(self, client_id):
        self.auth0.clients.delete(client_id)

    def get_client(self, client_id):
        return self.auth0.clients.get(client_id)

    def list_clients(self):
        return self.auth0.clients.list()

    def change_secret(self, client_id):
        c = [secrets.choice(self._chars) for x in range(self._secret_len)]
        secret = "".join(c)
        return self.auth0.clients.update(client_id, client_secret=secret)

    def create_non_interactive_client(self, name, description=None, callbacks=None):
        if callbacks is None:
            callbacks = []
        return self.auth0.clients.create(
            name=name,
            app_type="non_interactive",
            description=description or "",
            token_endpoint_auth_method="client_secret_basic",
            callbacks=callbacks,
        )

    def create_client_grant(self, client_id, audience, scopes):
        return self.auth0.client_grants.create(
            client_id=client_id,
            audience=audience,
            scope=scopes,
        )


class Auth0UserInfo(object):
    user_url = "/api/v2/users/{id}"

    def __init__(self, domain, token):
        self.domain = domain
        self.token = token
        self.auth0 = ManagementClient(domain=domain, token=token)

    def get_userinfo(self, user_id):
        return self.auth0.users.get(user_id)

    # https://datamermaid.auth0.com/userinfo


class Auth0ManagementAPI(object):
    def __init__(self, domain, client_id, client_secret):
        self.domain = domain
        self.client_id = client_id
        self.client_secret = client_secret

    def get_token(self):
        audience = settings.AUTH0_MANAGEMENT_API_AUDIENCE
        get_token = GetToken(self.domain, self.client_id, self.client_secret)
        try:
            token = get_token.client_credentials(audience)
            mgmt_api_token = token["access_token"]
            return mgmt_api_token
        except Auth0Error as e:
            if e.status_code == 429:
                logger.warning("[auth0.rate_limit] Management API rate limit hit: %s", e)
            else:
                logger.error(
                    "[auth0.service_unavailable] Management API error status=%s: %s",
                    e.status_code,
                    e,
                )
            raise Auth0ServiceUnavailable() from e
        except (ReadTimeout, Timeout, ConnectionError) as e:
            logger.error(
                "[auth0.service_unavailable] Management API timeout/connection error: %s", e
            )
            raise Auth0ServiceUnavailable() from e


def is_hs_token(token):
    try:
        jwt.decode(
            token,
            settings.MERMAID_API_SIGNING_SECRET,
            options={
                "verify_signature": False,
                "verify_aud": False,
                "verify_iat": False,
                "verify_exp": False,
                "verify_nbf": False,
                "verify_iss": False,
                "verify_sub": False,
                "verify_jti": False,
            },
        )
        return True
    except jwt.JWTError:
        return False


def get_jwt_token(request):
    token = None
    auth = get_authorization_header(request).split()

    if len(auth) == 2:
        auth_header_prefix = "Bearer"

        if not auth:
            return None

        if smart_str(auth[0].lower()) != auth_header_prefix.lower():
            return None

        token = auth[1]
    elif len(auth) > 2:
        msg = _("Invalid Authorization header. Credentials string should not contain spaces.")
        raise exceptions.AuthenticationFailed(msg)
    else:
        token = request.query_params.get("access_token")

    if token is None:
        msg = _("Invalid Authorization header. No credentials provided.")
        raise exceptions.AuthenticationFailed(msg)

    return token


def get_user_info(user_id):
    domain = settings.AUTH0_DOMAIN
    client_id = settings.MERMAID_MANAGEMENT_API_CLIENT_ID
    client_secret = settings.MERMAID_MANAGEMENT_API_CLIENT_SECRET

    auth = Auth0ManagementAPI(domain, client_id, client_secret)

    token = auth.get_token()
    auth_user = Auth0UserInfo(domain, token)
    try:
        ui = auth_user.get_userinfo(user_id)
    except ApiError as e:
        if e.status_code == 429:
            logger.warning("[auth0.rate_limit] User info API rate limit hit for %s: %s", user_id, e)
        else:
            logger.error(
                "[auth0.service_unavailable] User info API error status=%s for %s: %s",
                e.status_code,
                user_id,
                e,
            )
        raise Auth0ServiceUnavailable() from e
    except (ReadTimeout, Timeout, ConnectionError) as e:
        logger.error(
            "[auth0.service_unavailable] User info API timeout/connection error for %s: %s",
            user_id,
            e,
        )
        raise Auth0ServiceUnavailable() from e

    um = ui.user_metadata or {}
    email = um.get("email") or ui.email
    if not email:
        # Auth0 returned no email for this user (e.g. phone/SMS-only identity).
        # Fail fast here rather than letting a None email reach
        # get_or_create_safeish(Profile, email=None), which would recurse
        # forever on the NOT NULL constraint of Profile.email.
        raise KeyError("email")

    return dict(
        first_name=um.get("first_name") or ui.given_name or "",
        last_name=um.get("last_name") or ui.family_name or "",
        email=email,
        picture=ui.picture,
    )


def get_token_algorithm(token):
    unverified_header = jws.get_unverified_header(token)
    return unverified_header.get("alg")


def get_jwks():
    jwks = {}
    url = "https://{}/.well-known/jwks.json".format(settings.AUTH0_DOMAIN)
    resp = urlopen(url)
    if resp.getcode() != 200:
        return None

    keys = json.loads(resp.read()).get("keys") or []
    for key in keys:
        jwks[key["kid"]] = dict(
            kty=key["kty"], kid=key["kid"], use=key["use"], n=key["n"], e=key["e"]
        )
    return jwks


def decode_rsa(token):
    unverified_header = jwt.get_unverified_header(token)
    jwks = get_jwks()
    rsa_key = jwks.get(unverified_header["kid"])
    if rsa_key is None:
        msg = "Unable to find appropriate key"
        raise exceptions.ValidationError(msg, code=400)
    try:
        return jwt.decode(
            token,
            rsa_key,
            algorithms=["RS256"],
            audience=settings.SPA_ADMIN_CLIENT_ID,
            issuer="https://{}/".format(settings.AUTH0_DOMAIN),
            # access_token='',
            options={"verify_at_hash": False},
        )
    except jwt.ExpiredSignatureError:
        raise exceptions.AuthenticationFailed("token is expired")

    except jwt.JWTClaimsError as clmerr:
        print(clmerr)
        raise exceptions.AuthenticationFailed("incorrect claims")
    except Exception:
        msg = "Unable to parse authentication"
        raise exceptions.ValidationError(msg, code=400)


def decode_hs(token):
    try:
        return jwt.decode(
            token,
            settings.MERMAID_API_SIGNING_SECRET,
            audience=settings.MERMAID_API_AUDIENCE,
            algorithms=["HS256"],
        )
    except jwt.JWTError as e:
        logger.debug("Decode token failed: {}".format(str(e)))
        raise exceptions.AuthenticationFailed(e)


def decode(token):
    alg = get_token_algorithm(token)
    if alg == "RS256":
        return decode_rsa(token)
    elif alg == "HS256":
        return decode_hs(token)

    msg = "{} algorithm not supported".format(alg)
    raise exceptions.ValidationError(msg, code=400)


def get_unverified_profile(token):
    payload = jwt.get_unverified_claims(token)
    return _get_profile(payload)


def get_profile(token):
    payload = decode(token)
    return _get_profile(payload)


def _get_profile(payload):
    sub = payload.get("sub")
    if not sub:
        return None

    if "@clients" in sub:
        client_id = sub.split("@clients")[0]
        try:
            app = Application.objects.get(client_id=client_id)
            return app.profile
        except Application.DoesNotExist:
            return None
    elif "|" in sub:
        try:
            auth_user = AuthUser.objects.get(user_id=sub)
            return auth_user.profile
        except AuthUser.DoesNotExist:
            return None

    return None
