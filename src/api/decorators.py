import time


def timeit(method):
    def timed(*args, **kw):
        ts = time.time()
        result = method(*args, **kw)
        te = time.time()
        if "log_time" in kw:
            name = kw.get("log_name", method.__name__.upper())
            kw["log_time"][name] = int((te - ts) * 1000)
        else:
            print("%r  %2.2f ms" % (method.__name__, (te - ts) * 1000))
        return result

    return timed


def needs_instance(message):
    def _needs_instance(func):
        @functools.wraps(func)
        def wrapped(*args, **kwargs):

            # Assume it's a method.
            self = args[0]
            if self.instance is None:
                return self.error(self.identifier, _(message.format(self.name)))

            return func(*args, **kwargs)

        return wrapped

    return _needs_instance
