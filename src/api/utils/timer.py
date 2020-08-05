import time


class Timer:
    def __init__(self, name):
        self.name = name

    def __enter__(self):
        self.start_time = time.time()

    def __exit__(self, type, value, traceback):
        delta = time.time() - self.start_time
        self.delta = delta
        self.start_time = None

        print(f"{self.name}: {delta:.3f}s")
