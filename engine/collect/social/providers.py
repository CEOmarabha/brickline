"""Pluggable HTTP providers: Apify, SerpApi, Firecrawl. Tokens stay in the environment."""

from __future__ import annotations

import json
import urllib.request
from typing import Any
from urllib.parse import urlencode

from engine.collect.http import FetchError, default_headers, get_json
from engine.collect.social.config import DEFAULT_APIFY_ACTORS, env


def apify_enabled() -> bool:
    return bool(env("APIFY_TOKEN"))


def serpapi_enabled() -> bool:
    return bool(env("SERPAPI_API_KEY") or env("SERPAPI_KEY"))


def firecrawl_enabled() -> bool:
    return bool(env("FIRECRAWL_API_KEY"))


def apify_run(actor: str, payload: dict[str, Any], *, timeout: float = 180) -> list[dict]:
    """Run an Apify actor and return dataset items. actor is 'username/name' or a full ID."""
    token = env("APIFY_TOKEN")
    if not token:
        return []
    actor_id = actor.replace("/", "~")
    url = (
        f"https://api.apify.com/v2/acts/{actor_id}/run-sync-get-dataset-items"
        f"?{urlencode({'token': token, 'timeout': int(timeout)})}"
    )
    body = json.dumps(payload).encode()
    # get_bytes doesn't POST; use urllib via get_text's stack — dedicated POST below.
    return _post_json(url, body, timeout=timeout + 30)


def apify_actor(kind: str) -> str:
    override = {
        "facebook": env("APIFY_FACEBOOK_ACTOR"),
        "instagram": env("APIFY_INSTAGRAM_ACTOR"),
        "tiktok": env("APIFY_TIKTOK_ACTOR"),
        "eventbrite": env("APIFY_EVENTBRITE_ACTOR"),
        "meetup": env("APIFY_MEETUP_ACTOR"),
        "luma": env("APIFY_LUMA_ACTOR"),
        "allevents": env("APIFY_ALLEVENTS_ACTOR"),
        "x": env("APIFY_X_ACTOR"),
    }.get(kind, "")
    return override or DEFAULT_APIFY_ACTORS.get(kind, "")


def serpapi_search(query: str, engine: str = "google_events") -> list[dict]:
    key = env("SERPAPI_API_KEY") or env("SERPAPI_KEY")
    if not key:
        return []
    url = "https://serpapi.com/search.json?" + urlencode(
        {"engine": engine, "q": query, "api_key": key, "hl": "en"}
    )
    try:
        data = get_json(url, timeout=45)
    except FetchError:
        return []
    if not isinstance(data, dict):
        return []
    for key_name in ("events_results", "organic_results", "news_results", "inline_videos"):
        rows = data.get(key_name)
        if isinstance(rows, list):
            return rows
    return []


def firecrawl_scrape(url: str) -> str:
    key = env("FIRECRAWL_API_KEY")
    if not key:
        return ""
    endpoint = env("FIRECRAWL_API_URL") or "https://api.firecrawl.dev/v1/scrape"
    payload = json.dumps({"url": url, "formats": ["markdown", "html"]}).encode()
    try:
        data = _post_json(endpoint, payload, timeout=60, bearer=key)
    except FetchError:
        return ""
    if isinstance(data, dict):
        inner = data.get("data") if isinstance(data.get("data"), dict) else data
        return str(inner.get("markdown") or inner.get("html") or inner.get("content") or "")
    return ""


def _post_json(url: str, body: bytes, *, timeout: float, bearer: str | None = None) -> list | dict:
    headers = default_headers({"Content-Type": "application/json"})
    if bearer:
        headers["Authorization"] = f"Bearer {bearer}"
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", "replace")
    except Exception as exc:
        raise FetchError(f"POST failed for {url.split('?', 1)[0]}") from exc
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise FetchError("provider returned non-JSON") from exc
