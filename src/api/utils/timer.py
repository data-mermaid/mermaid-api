from functools import wraps
from time import time


class Timer:
    def __init__(self, name):
        self.name = name

    def __enter__(self):
        self.start_time = time()

    def __exit__(self, type, value, traceback):
        delta = time() - self.start_time
        self.delta = delta
        self.start_time = None

        print(f"{self.name}: {delta:.3f}s")


def timing(f):
    @wraps(f)
    def wrap(*args, **kw):
        ts = time()
        result = f(*args, **kw)
        te = time()
        print("func:%r took: %2.4f sec" % (f.__name__, te - ts))
        return result

    return wrap
