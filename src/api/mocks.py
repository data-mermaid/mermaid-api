from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist

from api.utils.tokenutils import create_token


class MockRequest:
    def __init__(
        self,
        user=None,
        token=None,
        query_params=None,
        GET=None,
        POST=None,
        data=None,
        profile=None,
        method="GET",
    ):
        if profile:
            username = profile.authusers.first().user_id
            user = get_user_model()(username=username, password="auth0")
            user.profile = profile
            self.user = user
        else:
            self.user = user
        self.method = method
        self.GET = GET or {}
        self.POST = POST or {}
        self.data = data or {}
        self.query_params = query_params or {}
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

    @classmethod
    def _check_for_token(cls, request):
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")
        if isinstance(auth_header, str) and auth_header.startswith("Bearer "):
            token = auth_header[7:]
            return token
        else:
            return None

    @classmethod
    def load_request(cls, request):
        data = {}
        if hasattr(request, "user"):
            data["user"] = request.user
        if hasattr(request.user, "profile"):
            data["profile"] = request.user.profile

        data["token"] = cls._check_for_token(request)
        data["GET"] = request.GET.dict()
        data["POST"] = request.POST.dict()
        data["data"] = request.data
        data["query_params"] = request.query_params.dict()

        if isinstance(request, MockRequest):
            return request
        return MockRequest(**data)
