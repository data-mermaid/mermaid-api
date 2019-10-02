class MockRequest:
    def __init__(self, user=None, token=None):
        self.user = user
        self.GET = {}
        self.query_params = {}
        if token:
            self.META = {"HTTP_AUTHORIZATION": "Bearer {}".format(token)}
        else:
            self.META = {}
