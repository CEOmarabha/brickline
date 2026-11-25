"""X (Twitter) public search via the official API, SerpApi, or Apify. No password login."""

from __future__ import annotations

from urllib.parse import urlencode

from engine.collect.http import FetchError, get_json
from engine.collect.social.config import INTENT_QUERIES, env
from engine.collect.social.providers import (
    apify_actor,
    apify_enabled,
    apify_run,
    serpapi_enabled,
    serpapi_search,
    tavily_enabled,
    tavily_search,
)
from engine.leads.event_models import RawEvent, strip_personal_contacts

PLACES = ("Chicago", "Milwaukee", "Hammond", "Gary IN")


def collect_x() -> tuple[list[RawEvent], list[dict]]:
    items: list[RawEvent] = []
    notes: list[dict] = []
    bearer = env("X_BEARER_TOKEN") or env("TWITTER_BEARER_TOKEN")
    if bearer:
        items.extend(_via_api(bearer))
    if not items and serpapi_enabled():
        items.extend(_via_serpapi())
    if not items and tavily_enabled():
        items.extend(_via_tavily())
    if not items and apify_enabled() and apify_actor("x"):
        items.extend(_via_apify())
    if not items:
        notes.append(
            {
                "source": "x",
                "status": "skipped",
                "detail": "set X_BEARER_TOKEN, SERPAPI_API_KEY, TAVILY_API_KEY, or APIFY_TOKEN + APIFY_X_ACTOR",
            }
        )
    return items, notes


def _via_api(bearer: str) -> list[RawEvent]:
    out: list[RawEvent] = []
    for intent in INTENT_QUERIES[:6]:
        for place in PLACES:
            q = f'"{intent}" {place}'
            url = "https://api.x.com/2/tweets/search/recent?" + urlencode(
                {"query": q, "max_results": "20", "tweet.fields": "created_at,text"}
            )
            try:
                data = get_json(url, timeout=30, headers={"Authorization": f"Bearer {bearer}"})
            except FetchError:
                continue
            for row in data.get("data") or []:
                tid = row.get("id")
                out.append(
                    RawEvent(
                        source="x",
                        source_url=f"https://x.com/i/web/status/{tid}" if tid else "https://x.com/",
                        title=(row.get("text") or "")[:80] or None,
                        start=(row.get("created_at") or "")[:10] or None,
                        text=strip_personal_contacts(row.get("text") or ""),
                        extra={"query": q},
                    )
                )
    return out


def _via_serpapi() -> list[RawEvent]:
    out: list[RawEvent] = []
    for intent in INTENT_QUERIES[:4]:
        for row in serpapi_search(f"{intent} Chicago", engine="google"):
            link = row.get("link") or ""
            if "x.com" not in link and "twitter.com" not in link:
                continue
            out.append(
                RawEvent(
                    source="x",
                    source_url=link,
                    title=row.get("title"),
                    text=strip_personal_contacts(row.get("snippet") or row.get("title") or ""),
                )
            )
    return out


def _via_tavily() -> list[RawEvent]:
    out: list[RawEvent] = []
    for intent in INTENT_QUERIES[:4]:
        for row in tavily_search(f"{intent} Chicago site:x.com"):
            link = row.get("link") or row.get("url") or ""
            if "x.com" not in link and "twitter.com" not in link:
                continue
            out.append(
                RawEvent(
                    source="x",
                    source_url=link,
                    title=row.get("title"),
                    text=strip_personal_contacts(row.get("snippet") or row.get("title") or ""),
                )
            )
    return out


def _via_apify() -> list[RawEvent]:
    rows = apify_run(
        apify_actor("x"), {"searchTerms": [f"{q} Chicago" for q in INTENT_QUERIES[:4]], "maxItems": 40}
    )
    out = []
    for row in rows if isinstance(rows, list) else []:
        if not isinstance(row, dict):
            continue
        out.append(
            RawEvent(
                source="x",
                source_url=row.get("url") or "https://x.com/",
                title=(row.get("text") or row.get("full_text") or "")[:80] or None,
                text=strip_personal_contacts(str(row.get("text") or row.get("full_text") or "")),
            )
        )
    return out
