import os
import time

from auth0.authentication import Database, GetToken
from auth0.management import ManagementClient
from auth0.management.errors import TooManyRequestsError
from django.conf import settings


class BaseAPI:
    def __init__(self, domain=None, client_id=None, client_secret=None, audience=None):
        self.domain = domain or settings.AUTH0_DOMAIN
        self.client_id = client_id or os.environ.get("MERMAID_MANAGEMENT_API_CLIENT_ID")
        self.client_secret = client_secret or os.environ.get("MERMAID_MANAGEMENT_API_CLIENT_SECRET")
        self.audience = audience or os.environ.get("AUTH0_MANAGEMENT_API_AUDIENCE")
        self._client = None
        self._token = None

    def get_token(self):
        get_token = GetToken(self.domain, self.client_id, self.client_secret)
        token = get_token.client_credentials(self.audience)
        mgmt_api_token = token["access_token"]
        return mgmt_api_token


class Auth0DatabaseAuthenticationAPI(BaseAPI):
    CONNECTION = "Username-Password-Authentication"

    @property
    def client(self):
        return Database(self.domain, self.client_id)

    def change_password(self, email):
        return self.client.change_password(email, self.CONNECTION)


class Auth0ManagementAPI(BaseAPI):
    @property
    def client(self):
        if self._client and self._token:
            return self._client

        # Check token is valid
        self._token = self.get_token()
        self._client = ManagementClient(domain=self.domain, token=self._token)
        return self._client


class Auth0Users(Auth0ManagementAPI):
    UPDATABLE_ATTRIBUTES = (
        "blocked",
        "email_verified",
        "email",
        "verify_email",
        "password",
        "phone_number",
        "phone_verified",
        "user_metadata",
        "app_metadata",
        "username",
    )

    def get_user_sets(self, query=None):
        client = self.client
        page = 0
        while True:
            try:
                resp = client.users.list(page=page, per_page=100, q=query, search_engine="v2")
            except TooManyRequestsError:
                # Rate limit exceeded
                time.sleep(1)
                continue

            yield resp.items or []
            if not resp.has_next:
                break
            page += 1

    def get_user_by_email(self, email):
        query = 'email.raw:"{}"'.format(email)
        users = []
        for user_set in self.get_user_sets(query=query):
            users.extend(list(user_set))
        return users

    def get_user(self, user_id):
        user = self.client.users.get(user_id)
        return user

    def update(self, user):
        user_id = user.pop("user_id")
        if user_id is None:
            raise ValueError("user_id missing")

        data = {key: val for key, val in user.items() if key in self.UPDATABLE_ATTRIBUTES}

        return self.client.users.update(user_id, **data)
