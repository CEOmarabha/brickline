"""Pluggable HTTP providers: Apify, SerpApi, Firecrawl, Tavily, Jina Reader. Tokens stay in the environment."""

from __future__ import annotations

import json
import urllib.request
from typing import Any
from urllib.parse import urlencode

from engine.collect.http import FetchError, default_headers, get_json, get_text
from engine.collect.social.browser import fetch_public_html
from engine.collect.social.config import DEFAULT_APIFY_ACTORS, env


def apify_enabled() -> bool:
    return bool(env("APIFY_TOKEN"))


def serpapi_enabled() -> bool:
    return bool(env("SERPAPI_API_KEY") or env("SERPAPI_KEY"))


def firecrawl_enabled() -> bool:
    return bool(env("FIRECRAWL_API_KEY") or env("FIRECRAWL_API_URL"))


def tavily_enabled() -> bool:
    return bool(env("TAVILY_API_KEY"))


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
    endpoint = env("FIRECRAWL_API_URL") or "https://api.firecrawl.dev/v1/scrape"
    if not key and not env("FIRECRAWL_API_URL"):
        return ""
    payload = json.dumps({"url": url, "formats": ["markdown", "html"]}).encode()
    try:
        data = _post_json(endpoint, payload, timeout=60, bearer=key or None)
    except FetchError:
        return ""
    if isinstance(data, dict):
        inner = data.get("data") if isinstance(data.get("data"), dict) else data
        return str(inner.get("markdown") or inner.get("html") or inner.get("content") or "")
    return ""


def tavily_search(query: str, *, max_results: int = 10) -> list[dict]:
    """Web search via Tavily. Returns rows with title/link/snippet (SerpApi-shaped)."""
    key = env("TAVILY_API_KEY")
    if not key:
        return []
    payload = json.dumps(
        {
            "api_key": key,
            "query": query,
            "search_depth": "basic",
            "include_answer": False,
            "max_results": max_results,
        }
    ).encode()
    try:
        data = _post_json("https://api.tavily.com/search", payload, timeout=45)
    except FetchError:
        return []
    rows = data.get("results") if isinstance(data, dict) else None
    if not isinstance(rows, list):
        return []
    out = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        out.append(
            {
                "title": row.get("title"),
                "link": row.get("url") or row.get("link"),
                "url": row.get("url") or row.get("link"),
                "snippet": row.get("content") or row.get("snippet") or "",
                "description": row.get("content") or row.get("description") or "",
            }
        )
    return out


def jina_read(url: str) -> str:
    """Free public-page fetch via Jina Reader (https://r.jina.ai/<url>). No API key."""
    base = (env("JINA_READER_URL") or "https://r.jina.ai").rstrip("/")
    target = url if url.startswith("http") else f"https://{url}"
    try:
        return get_text(
            f"{base}/{target}",
            timeout=45,
            attempts=2,
            headers={"Accept": "text/plain"},
        )
    except FetchError:
        return ""


def page_looks_blocked(text: str) -> bool:
    low = (text or "").lower()
    return any(
        marker in low
        for marker in (
            "confirm you are human",
            "complete the security check",
            "please verify you are a human",
            "attention required",
        )
    )


def fetch_public_page(url: str) -> str:
    """Public HTML/markdown: Firecrawl when keyed, else direct GET, else Jina, else Playwright."""
    if firecrawl_enabled():
        text = firecrawl_scrape(url)
        if text.strip() and not page_looks_blocked(text):
            return text
    try:
        text = get_text(url, timeout=30, attempts=2)
    except FetchError:
        text = ""
    if text.strip() and not page_looks_blocked(text):
        return text
    text = jina_read(url)
    if text.strip() and not page_looks_blocked(text):
        return text
    return fetch_public_html(url)


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
