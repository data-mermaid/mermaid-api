from ...permissions import REQUEST_CACHE_ATTRS


class ViewRequest:
    def __init__(self, user, headers, method="GET"):
        self.user = user
        self.data = {}
        self.query_params = {}
        self.GET = {}
        self.META = {}
        self.method = method
        self.headers = headers


def create_view_request(request, method=None, data=None):
    data = data or {}

    method = method or request.method
    vw_request = ViewRequest(user=request.user, headers=request.headers, method=method)
    for k, v in data.items():
        vw_request.data[k] = v

    vw_request.META = request.META
    vw_request.authenticators = request.authenticators
    vw_request.successful_authenticator = request.successful_authenticator

    # Per-request memoization caches used by api.permissions (get_project,
    # get_project_profile). Pull/push build a fresh ViewRequest per source type
    # (and, for push, per record), so these are lazily created on the original
    # `request` here and shared by reference with every derived ViewRequest -
    # otherwise each derived request would start with an empty cache and repeated
    # permission checks against the same project/profile would re-query every time.
    for attr in REQUEST_CACHE_ATTRS:
        if getattr(request, attr, None) is None:
            setattr(request, attr, {})
        setattr(vw_request, attr, getattr(request, attr))

    return vw_request
