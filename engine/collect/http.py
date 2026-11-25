"""One GET with a timeout and retries, shared by the bulk collectors."""

from __future__ import annotations

import http.client
import json
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
from functools import lru_cache

RETRY_STATUS = frozenset({408, 425, 429, 500, 502, 503, 504})
# URLError, TimeoutError and ConnectionError are all OSError; a body cut short raises IncompleteRead instead.
TRANSIENT = (OSError, http.client.HTTPException)
USER_AGENT = "BricklineResearchBot/0.1 (public-records research; +contact: founder)"
ROBOT_TOKEN = "BricklineResearchBot"


class FetchError(RuntimeError):
    """A download that failed for good. `status` is the HTTP status when the server answered, else None."""

    def __init__(self, message: str, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


def default_headers(extra: dict[str, str] | None = None) -> dict[str, str]:
    headers = {"User-Agent": USER_AGENT, "Accept": "*/*"}
    if extra:
        headers.update(extra)
    return headers


@lru_cache(maxsize=64)
def robots_allowed(url: str, user_agent: str = ROBOT_TOKEN) -> bool:
    """True when robots.txt allows this path, or when robots.txt is missing/unreadable.

    A 401/403 on robots.txt is treated as no crawl (same rule as engine.enrich.web).
    """
    parts = urllib.parse.urlsplit(url)
    robots_url = f"{parts.scheme}://{parts.netloc}/robots.txt"
    parser = urllib.robotparser.RobotFileParser()
    try:
        req = urllib.request.Request(robots_url, headers=default_headers())
        with urllib.request.urlopen(req, timeout=15) as resp:
            status = getattr(resp, "status", 200)
            if status in {401, 403}:
                return False
            parser.parse(resp.read().decode("utf-8", "replace").splitlines())
    except urllib.error.HTTPError as exc:
        if exc.code in {401, 403}:
            return False
        return True
    except (OSError, http.client.HTTPException, UnicodeError):
        return True
    return parser.can_fetch(user_agent, url)


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
    req = urllib.request.Request(url, headers=default_headers(headers))
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


def get_text(
    url: str, *, timeout: float = 60, attempts: int = 4, headers: dict[str, str] | None = None
) -> str:
    return get_bytes(url, timeout=timeout, attempts=attempts, headers=headers).decode("utf-8", "replace")


def get_json(url: str, *, timeout: float = 60, attempts: int = 4, headers: dict[str, str] | None = None):
    return json.loads(get_text(url, timeout=timeout, attempts=attempts, headers=headers))
