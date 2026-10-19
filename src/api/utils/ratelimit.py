"""Failure rate limiting for credential checks (C8 of the API key plan).

An API key secret is 256 bits, so guessing it is not the threat. The threat is
a client (or an attacker with a leaked-and-revoked key) hammering the API with
a bad credential: it costs a database lookup and a hash per request, and it
buries the real signal in the log. Counting failures and answering 429 for the
rest of the minute makes that loud and cheap.

The window is aligned to the wall clock and is part of the cache key, so a
window needs no expiry bookkeeping of its own: it simply stops being read.
Counting is deliberately approximate. Two workers can miss the same key and
both create it, losing a failure; that costs an attacker nothing and is not
worth a lock on the default cache, which is `DatabaseCache`.
"""

import math
import time

from django.core.cache import cache


class FailureRateLimiter:
    """Counts failures per identifier in fixed windows and blocks past a limit.

    `namespace` prefixes the cache keys so limiters do not collide; `scope`
    separates the kinds of identifier being counted (an IP from a key id, say)
    so a value that could appear as both cannot pool its failures.
    """

    def __init__(self, namespace, limit, window=60):
        self.namespace = namespace
        self.limit = limit
        self.window = window

    def _window_start(self, now):
        return int(now // self.window) * self.window

    def _cache_key(self, scope, identifier, window_start):
        return f"{self.namespace}:fail:{scope}:{identifier}:{window_start}"

    def retry_after(self, scope, identifier):
        """Seconds left in this window if the identifier is over the limit.

        Returns `None` when it is not, so the caller can treat this as a
        "should I block" question.
        """

        now = time.time()
        window_start = self._window_start(now)
        count = cache.get(self._cache_key(scope, identifier, window_start)) or 0
        if count < self.limit:
            return None
        # At least a second: DRF renders this into Retry-After, and 0 reads as
        # "try again immediately", which is the opposite of what happened.
        return max(1, math.ceil(window_start + self.window - now))

    def record_failure(self, scope, identifier):
        """Count one failure and return the running total for this window."""

        now = time.time()
        window_start = self._window_start(now)
        cache_key = self._cache_key(scope, identifier, window_start)
        # Expire with the window rather than after a full `window` from now, so
        # a busy limiter does not leave a trail of rows in DatabaseCache.
        timeout = max(1, math.ceil(window_start + self.window - now))

        try:
            return cache.incr(cache_key)
        except ValueError:
            # No counter yet for this window.
            pass

        if cache.add(cache_key, 1, timeout):
            return 1

        # Another worker created it between the incr and the add.
        try:
            return cache.incr(cache_key)
        except ValueError:
            return 1

    def reset(self, scope, identifier):
        """Forget an identifier's failures. Used by tests and by admin repair."""

        cache.delete(self._cache_key(scope, identifier, self._window_start(time.time())))
