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

    return vw_request
