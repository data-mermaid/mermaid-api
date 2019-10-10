class MockRequest:
    def __init__(self, user=None, token=None, query_params=None, GET=None):
        self.user = user
        self.GET = GET or dict()
        self.query_params = query_params or dict()
        if token:
            self.META = {"HTTP_AUTHORIZATION": "Bearer {}".format(token)}
        else:
            self.META = {}
