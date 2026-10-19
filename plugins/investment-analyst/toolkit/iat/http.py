"""Small HTTP helpers with retries and polite rate limiting."""
from __future__ import annotations

import time

import requests

DEFAULT_UA = "iat-toolkit/0.1 (+https://github.com)"


class RateLimiter:
    def __init__(self, per_second: float):
        self.min_interval = 1.0 / per_second
        self._last = 0.0

    def wait(self) -> None:
        delta = time.monotonic() - self._last
        if delta < self.min_interval:
            time.sleep(self.min_interval - delta)
        self._last = time.monotonic()


def get(url: str, *, headers: dict | None = None, params: dict | None = None, timeout: int = 60,
        retries: int = 3, backoff: float = 2.0, limiter: RateLimiter | None = None) -> requests.Response:
    """GET with retry on 429/5xx and connection errors. Raises on final failure."""
    headers = {"User-Agent": DEFAULT_UA, **(headers or {})}
    last_exc: Exception | None = None
    for attempt in range(retries + 1):
        if limiter:
            limiter.wait()
        try:
            r = requests.get(url, headers=headers, params=params, timeout=timeout)
            if r.status_code in (429, 500, 502, 503, 504):
                raise requests.HTTPError(f"HTTP {r.status_code} for {url}", response=r)
            r.raise_for_status()
            return r
        except (requests.ConnectionError, requests.Timeout, requests.HTTPError) as exc:
            last_exc = exc
            status = getattr(getattr(exc, "response", None), "status_code", None)
            if status is not None and status not in (429, 500, 502, 503, 504):
                raise
            if attempt < retries:
                time.sleep(backoff * (2 ** attempt))
    assert last_exc is not None
    raise last_exc
