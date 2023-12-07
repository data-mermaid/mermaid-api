from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist

from api.utils.tokenutils import create_token


class MockRequest:
    def __init__(self, user=None, token=None, query_params=None, GET=None, profile=None):
        if profile:
            username = profile.authusers.first().user_id
            user = get_user_model()(username=username, password="auth0")
            user.profile = profile
            self.user = user
        else:
            self.user = user
        self.GET = GET or dict()
        self.query_params = query_params or dict()
        if not token and self.user:
            try:
                auth_user = self.user.profile.authusers.first()
                token = create_token(auth_user.user_id)
            except ObjectDoesNotExist:
                pass

        if token:
            self.META = {"HTTP_AUTHORIZATION": "Bearer {}".format(token)}
        else:
            self.META = {}
