"""Instagram public profiles and hashtags via session cookies or Apify."""

from __future__ import annotations

import html as htmlmod
import re
from urllib.parse import quote_plus

from engine.collect.social.browser import crawl_pages
from engine.collect.social.config import env, queries_for_region
from engine.collect.social.providers import apify_actor, apify_enabled, apify_run
from engine.collect.social.session import SessionExpired, load_cookie_header, session_configured
from engine.collect.social.throttle import Throttle
from engine.leads.event_models import RawEvent, strip_personal_contacts

HREF_RE = re.compile(r'href="(https?://(?:www\.)?instagram\.com/[^"]+)"', re.I)
CAPTION_RE = re.compile(r'"caption"\s*:\s*"((?:\\.|[^"\\])*)"', re.I)
HASHTAGS = (
    "chicagowedding",
    "chicagoweddings",
    "chicagoquinceanera",
    "milwaukeewedding",
    "nwiwedding",
    "chicagoparty",
)


def collect_instagram(*, authenticated: bool = True) -> tuple[list[RawEvent], list[dict]]:
    notes: list[dict] = []
    items: list[RawEvent] = []
    if not authenticated:
        return items, notes
    try:
        batch, skip = _via_playwright()
        items.extend(batch)
        if skip:
            notes.append({"source": "instagram_playwright", "status": "skipped", "detail": skip})
    except SessionExpired as exc:
        notes.append({"source": "instagram", "status": "session_expired", "detail": str(exc)})
    except Exception as exc:
        notes.append({"source": "instagram_playwright", "status": "error", "detail": type(exc).__name__})
    if not items:
        items.extend(_via_apify())
    if not session_configured("instagram") and not apify_enabled():
        notes.append(
            {"source": "instagram", "status": "skipped", "detail": "set IG_STORAGE_STATE or APIFY_TOKEN"}
        )
    return items, notes


def _urls() -> list[str]:
    urls = [f"https://www.instagram.com/explore/tags/{tag}/" for tag in HASHTAGS]
    extra = env("IG_PROFILE_URLS")
    urls.extend(u.strip() for u in extra.split(",") if u.strip())
    for query, _region in queries_for_region()[:8]:
        urls.append(f"https://www.instagram.com/explore/search/keyword/?q={quote_plus(query)}")
    return list(dict.fromkeys(urls))[:16]


def _via_playwright() -> tuple[list[RawEvent], str | None]:
    throttle = Throttle("instagram", min_delay=12, max_delay=28, max_per_run=16, max_per_hour=36)
    rows, skip = crawl_pages("instagram", _urls(), _extract, throttle)
    return [_item(r) for r in rows], skip


def _via_apify() -> list[RawEvent]:
    if not apify_enabled():
        return []
    actor = apify_actor("instagram")
    cookie = load_cookie_header("instagram")
    payload = {
        "directUrls": [f"https://www.instagram.com/explore/tags/{t}/" for t in HASHTAGS[:4]],
        "resultsType": "posts",
        "resultsLimit": 40,
    }
    if cookie:
        payload["cookie"] = cookie
        payload["cookies"] = cookie
    rows = apify_run(actor, payload)
    out = []
    for row in rows if isinstance(rows, list) else []:
        if not isinstance(row, dict):
            continue
        out.append(
            _item(
                {
                    "url": row.get("url") or row.get("inputUrl") or "https://www.instagram.com/",
                    "title": (row.get("caption") or "")[:80] or None,
                    "text": row.get("caption") or row.get("text") or "",
                }
            )
        )
    return out


def _extract(page_url: str, html: str) -> list[dict]:
    found = []
    for href in HREF_RE.findall(html):
        href = htmlmod.unescape(href).split("?")[0]
        if "/p/" in href or "/reel/" in href:
            found.append({"url": href, "title": None, "text": "", "page": page_url})
    captions = [
        htmlmod.unescape(m.replace("\\n", " ").replace('\\"', '"')) for m in CAPTION_RE.findall(html)[:8]
    ]
    blob = " ".join(c for c in captions if c)[:1500]
    if blob:
        found.append({"url": page_url, "title": None, "text": blob, "page": page_url})
    return found[:25]


def _item(row: dict) -> RawEvent:
    text = strip_personal_contacts(str(row.get("text") or ""))
    region = None
    low = text.lower() + " " + (row.get("page") or "")
    if "milwaukee" in low:
        region = "milwaukee"
    elif any(w in low for w in ("nwi", "indiana", "gary", "hammond")):
        region = "nw_indiana"
    elif "chicago" in low:
        region = "chicagoland"
    return RawEvent(
        source="instagram",
        source_url=row.get("url") or "https://www.instagram.com/",
        title=row.get("title"),
        region=region,
        text=text,
        extra={"page": row.get("page")},
    )
