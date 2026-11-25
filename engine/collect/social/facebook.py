"""Facebook public events, pages, and joined groups via session cookies or Apify."""

from __future__ import annotations

import html as htmlmod
import re
from urllib.parse import quote_plus, urlparse

from engine.collect.social.browser import crawl_pages
from engine.collect.social.config import env, queries_for_region
from engine.collect.social.providers import apify_actor, apify_enabled, apify_run
from engine.collect.social.session import SessionExpired, load_cookie_header, session_configured
from engine.collect.social.throttle import Throttle
from engine.leads.event_models import RawEvent, strip_personal_contacts

HREF_RE = re.compile(r'href="(https?://(?:www\.)?facebook\.com/[^"]+)"', re.I)
EVENT_HREF = re.compile(r"facebook\.com/events/\d+", re.I)
GROUP_POST = re.compile(r"facebook\.com/groups/[^/\"?]+/(?:posts|permalink)/", re.I)
TEXT_RE = re.compile(r"<p[^>]*>(.*?)</p>", re.I | re.S)
TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)


def collect_facebook(*, authenticated: bool = True) -> tuple[list[RawEvent], list[dict]]:
    notes: list[dict] = []
    items: list[RawEvent] = []
    if not authenticated:
        return items, notes
    try:
        batch, skip = _via_playwright()
        items.extend(batch)
        if skip:
            notes.append({"source": "facebook_playwright", "status": "skipped", "detail": skip})
    except SessionExpired as exc:
        notes.append({"source": "facebook", "status": "session_expired", "detail": str(exc)})
    except Exception as exc:
        notes.append({"source": "facebook_playwright", "status": "error", "detail": type(exc).__name__})
    if not items:
        items.extend(_via_apify())
    if not session_configured("facebook") and not apify_enabled():
        notes.append(
            {
                "source": "facebook",
                "status": "skipped",
                "detail": "set FB_STORAGE_STATE / FB_COOKIES_FILE or APIFY_TOKEN (docs/21-event-lead-scanner.md)",
            }
        )
    elif not items and not any(n.get("status") == "session_expired" for n in notes):
        notes.append({"source": "facebook", "status": "empty"})
    return items, notes


def _search_urls() -> list[tuple[str, str | None]]:
    """(url, region hint) for events, public search, and joined groups. Cap so a first run cannot hammer the account."""
    extra = env("FB_GROUP_URLS")
    urls: list[tuple[str, str | None]] = []
    for u in extra.split(","):
        u = u.strip()
        if u:
            urls.append((u, _region_from_text(u)))
    urls.append(("https://www.facebook.com/events/", None))
    urls.append(("https://www.facebook.com/events/discovery/", None))
    urls.append(("https://www.facebook.com/groups/feed/", None))
    urls.append(("https://www.facebook.com/groups/?category=membership", None))
    for query, region in queries_for_region()[:12]:
        q = quote_plus(query)
        urls.append((f"https://www.facebook.com/search/events?q={q}", region))
        urls.append((f"https://www.facebook.com/groups/search/groups?q={q}", region))
        urls.append((f"https://www.facebook.com/search/posts?q={q}", region))
    seen: set[str] = set()
    out = []
    for url, region in urls:
        if url in seen:
            continue
        seen.add(url)
        out.append((url, region))
        if len(out) >= 20:
            break
    return out


def _via_playwright() -> tuple[list[RawEvent], str | None]:
    throttle = Throttle("facebook", min_delay=15, max_delay=32, max_per_run=18, max_per_hour=40)
    planned = _search_urls()
    by_url = {u: r for u, r in planned}

    def extract(page_url: str, html: str) -> list[dict]:
        rows = _extract(page_url, html)
        region = by_url.get(page_url)
        for row in rows:
            row["region"] = region or _region_from_text(row.get("text") or page_url)
        return rows

    rows, skip = crawl_pages("facebook", [u for u, _ in planned], extract, throttle)
    return [_item(r) for r in rows], skip


def _via_apify() -> list[RawEvent]:
    if not apify_enabled():
        return []
    actor = apify_actor("facebook")
    if not actor:
        return []
    cookie = load_cookie_header("facebook")
    payload: dict = {
        "searchMode": "events",
        "query": "Chicago wedding OR Milwaukee festival OR quinceanera Chicago",
        "maxItems": 50,
        "location": "Chicago, IL",
    }
    groups = [u.strip() for u in env("FB_GROUP_URLS").split(",") if u.strip()]
    if groups:
        payload["groupUrls"] = groups[:8]
    if cookie:
        payload["cookie"] = cookie
        payload["cookies"] = cookie
    rows = apify_run(actor, payload)
    out = []
    for row in rows if isinstance(rows, list) else []:
        if not isinstance(row, dict):
            continue
        text = str(row.get("description") or row.get("text") or "")
        out.append(
            _item(
                {
                    "url": row.get("url") or row.get("eventUrl") or "https://www.facebook.com/events/",
                    "title": row.get("name") or row.get("title"),
                    "text": text,
                    "start": row.get("startDate") or row.get("date"),
                    "venue": row.get("location") or row.get("venueName"),
                    "region": _region_from_text(text + " " + str(row.get("location") or "")),
                }
            )
        )
    return out


def _extract(page_url: str, html: str) -> list[dict]:
    found = []
    seen = set()
    title_m = TITLE_RE.search(html)
    page_title = re.sub(r"<[^>]+>", " ", htmlmod.unescape(title_m.group(1))).strip() if title_m else None
    for href in HREF_RE.findall(html):
        href = htmlmod.unescape(href).split("?")[0]
        if href in seen:
            continue
        seen.add(href)
        if EVENT_HREF.search(href) or GROUP_POST.search(href) or "/groups/" in href:
            found.append({"url": href, "title": page_title, "text": "", "page": page_url})
    blobs = [re.sub(r"<[^>]+>", " ", htmlmod.unescape(m)).strip() for m in TEXT_RE.findall(html)]
    text = " ".join(b for b in blobs if 40 < len(b) < 400)[:1500]
    if text:
        found.append({"url": page_url, "title": page_title, "text": text, "page": page_url})
    return found[:30]


def _item(row: dict) -> RawEvent:
    host = urlparse(row.get("url") or "").netloc
    kind = "group" if "/groups/" in (row.get("url") or "") else "event"
    return RawEvent(
        source="facebook",
        source_url=row.get("url") or "https://www.facebook.com/",
        title=row.get("title"),
        start=str(row["start"])[:10] if row.get("start") else None,
        venue=row.get("venue") if isinstance(row.get("venue"), str) else None,
        region=row.get("region") if isinstance(row.get("region"), str) else None,
        text=strip_personal_contacts(str(row.get("text") or row.get("title") or "")),
        extra={"page": row.get("page"), "kind": kind, "host": host},
    )


def _region_from_text(text: str) -> str | None:
    low = text.lower()
    if any(w in low for w in ("milwaukee", "waukesha", "racine", "kenosha")):
        return "milwaukee"
    if any(w in low for w in ("hammond", "gary", "munster", "nwi", "indiana", "valparaiso")):
        return "nw_indiana"
    if any(w in low for w in ("chicago", "evanston", "naperville", "illinois")):
        return "chicagoland"
    return None
