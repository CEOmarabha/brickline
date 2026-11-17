"""One GET with a timeout and retries, shared by the bulk collectors."""

from __future__ import annotations

import http.client
import time
import urllib.error
import urllib.request

RETRY_STATUS = frozenset({408, 425, 429, 500, 502, 503, 504})
# URLError, TimeoutError and ConnectionError are all OSError; a body cut short raises IncompleteRead instead.
TRANSIENT = (OSError, http.client.HTTPException)


class FetchError(RuntimeError):
    """A download that failed for good. `status` is the HTTP status when the server answered, else None."""

    def __init__(self, message: str, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


def get_bytes(
    url: str,
    *,
    timeout: float = 600,
    attempts: int = 5,
    headers: dict[str, str] | None = None,
    sleep=time.sleep,
) -> bytes:
    """Body of `url`. Retries timeouts, dropped connections and 408/425/429/5xx with exponential backoff
    (4, 8, 16, ... seconds); any other HTTP error (400, 403, 404) is final at once."""
    req = urllib.request.Request(url, headers=headers or {})
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except urllib.error.HTTPError as exc:
            if exc.code not in RETRY_STATUS or attempt == attempts - 1:
                raise FetchError(f"HTTP {exc.code} for {url}", exc.code) from exc
        except TRANSIENT as exc:
            if attempt == attempts - 1:
                raise FetchError(f"download failed after {attempts} attempts: {url} ({exc})") from exc
        sleep(4 * 2**attempt)
    raise AssertionError("unreachable")
