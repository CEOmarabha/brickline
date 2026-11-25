"""TikTok public posts via session cookies or Apify."""

from __future__ import annotations

import html as htmlmod
import re
from urllib.parse import quote_plus

from engine.collect.social.browser import crawl_pages
from engine.collect.social.config import queries_for_region
from engine.collect.social.providers import apify_actor, apify_enabled, apify_run
from engine.collect.social.session import SessionExpired, load_cookie_header, session_configured
from engine.collect.social.throttle import Throttle
from engine.leads.event_models import RawEvent, strip_personal_contacts

HREF_RE = re.compile(r'href="(https?://(?:www\.)?tiktok\.com/[^"]+)"', re.I)
DESC_RE = re.compile(r'"desc"\s*:\s*"((?:\\.|[^"\\])*)"', re.I)
TAGS = ("chicagowedding", "chicagoevents", "milwaukeewedding", "quinceanera")


def collect_tiktok(*, authenticated: bool = True) -> tuple[list[RawEvent], list[dict]]:
    notes: list[dict] = []
    items: list[RawEvent] = []
    if not authenticated:
        return items, notes
    try:
        batch, skip = _via_playwright()
        items.extend(batch)
        if skip:
            notes.append({"source": "tiktok_playwright", "status": "skipped", "detail": skip})
    except SessionExpired as exc:
        notes.append({"source": "tiktok", "status": "session_expired", "detail": str(exc)})
    except Exception as exc:
        notes.append({"source": "tiktok_playwright", "status": "error", "detail": type(exc).__name__})
    if not items:
        items.extend(_via_apify())
    if not session_configured("tiktok") and not apify_enabled():
        notes.append(
            {"source": "tiktok", "status": "skipped", "detail": "set TIKTOK_STORAGE_STATE or APIFY_TOKEN"}
        )
    return items, notes


def _urls() -> list[str]:
    urls = [f"https://www.tiktok.com/tag/{tag}" for tag in TAGS]
    for query, _region in queries_for_region()[:8]:
        urls.append(f"https://www.tiktok.com/search?q={quote_plus(query)}")
    return list(dict.fromkeys(urls))[:12]


def _via_playwright() -> tuple[list[RawEvent], str | None]:
    throttle = Throttle("tiktok", min_delay=12, max_delay=30, max_per_run=14, max_per_hour=32)
    rows, skip = crawl_pages("tiktok", _urls(), _extract, throttle)
    return [_item(r) for r in rows], skip


def _via_apify() -> list[RawEvent]:
    if not apify_enabled():
        return []
    actor = apify_actor("tiktok")
    cookie = load_cookie_header("tiktok")
    payload = {
        "searchQueries": [f"{intent} Chicago" for intent in ("wedding", "quinceanera", "looking for a DJ")],
        "maxItems": 40,
    }
    if cookie:
        payload["cookies"] = cookie
        payload["cookie"] = cookie
    rows = apify_run(actor, payload)
    out = []
    for row in rows if isinstance(rows, list) else []:
        if not isinstance(row, dict):
            continue
        out.append(
            _item(
                {
                    "url": row.get("webVideoUrl") or row.get("url") or "https://www.tiktok.com/",
                    "title": (row.get("text") or "")[:80] or None,
                    "text": row.get("text") or "",
                }
            )
        )
    return out


def _extract(page_url: str, html: str) -> list[dict]:
    found = []
    for href in HREF_RE.findall(html):
        href = htmlmod.unescape(href).split("?")[0]
        if "/video/" in href:
            found.append({"url": href, "title": None, "text": "", "page": page_url})
    descs = [htmlmod.unescape(m.replace("\\n", " ").replace('\\"', '"')) for m in DESC_RE.findall(html)[:8]]
    blob = " ".join(d for d in descs if d)[:1500]
    if blob:
        found.append({"url": page_url, "title": None, "text": blob, "page": page_url})
    return found[:25]


def _item(row: dict) -> RawEvent:
    text = strip_personal_contacts(str(row.get("text") or ""))
    low = text.lower() + " " + (row.get("page") or "")
    region = None
    if "milwaukee" in low:
        region = "milwaukee"
    elif any(w in low for w in ("nwi", "indiana", "gary", "hammond")):
        region = "nw_indiana"
    elif "chicago" in low:
        region = "chicagoland"
    return RawEvent(
        source="tiktok",
        source_url=row.get("url") or "https://www.tiktok.com/",
        title=row.get("title"),
        region=region,
        text=text,
        extra={"page": row.get("page")},
    )
