"""Eventbrite, Meetup, Luma and AllEvents via feeds, official APIs, or providers."""

from __future__ import annotations

import re
from urllib.parse import urlparse

from engine.collect.event_feeds import _rss_items, collect_ical_urls, parse_ics
from engine.collect.http import FetchError, get_text, robots_allowed
from engine.collect.social.config import env
from engine.collect.social.providers import (
    apify_actor,
    apify_enabled,
    apify_run,
    fetch_public_page,
    firecrawl_enabled,
    firecrawl_scrape,
    serpapi_enabled,
    serpapi_search,
    tavily_enabled,
    tavily_search,
)
from engine.leads.event_models import RawEvent, strip_personal_contacts

LUMA_PAGES = (
    "https://lu.ma/chicago",
    "https://lu.ma/milwaukee",
)
ALLEVENTS_PAGES = (
    "https://allevents.in/chicago",
    "https://allevents.in/milwaukee",
    "https://allevents.in/gary",
)
# Public Eventbrite city directories. The old /v3/events/search API is retired.
EVENTBRITE_CITY_PAGES = (
    ("https://www.eventbrite.com/d/il--chicago/events/", "chicagoland", "Chicago"),
    ("https://www.eventbrite.com/d/il--chicago/wedding/", "chicagoland", "Chicago"),
    ("https://www.eventbrite.com/d/wi--milwaukee/events/", "milwaukee", "Milwaukee"),
    ("https://www.eventbrite.com/d/in--gary/events/", "nw_indiana", "Gary"),
)
EVENTBRITE_URL_RE = re.compile(
    r"https?://(?:www\.)?eventbrite\.com/e/[a-z0-9\-]+(?:\?[^\s\"'<>]*)?",
    re.I,
)
EVENTBRITE_SLUG_RE = re.compile(r"/e/([a-z0-9\-]+?)(?:-tickets)?-(\d+)", re.I)


def collect_listings() -> tuple[list[RawEvent], list[dict]]:
    items: list[RawEvent] = []
    notes: list[dict] = []
    eb, eb_notes = collect_eventbrite()
    items.extend(eb)
    notes.extend(eb_notes)
    items.extend(collect_meetup())
    luma, luma_note = collect_luma()
    items.extend(luma)
    notes.extend(luma_note)
    ae, ae_note = collect_allevents()
    items.extend(ae)
    notes.extend(ae_note)
    extra = env("EVENT_ICAL_URLS")
    if extra:
        items.extend(collect_ical_urls([u for u in extra.split(",") if u.strip()]))
    return items, notes


def collect_eventbrite() -> tuple[list[RawEvent], list[dict]]:
    """Public city pages via Jina / Playwright / Firecrawl. Optional Tavily, SerpApi, Apify."""
    notes: list[dict] = []
    out = _eventbrite_from_city_pages()
    if out:
        notes.append({"source": "eventbrite", "status": "ok", "count": len(out), "via": "public_pages"})
        return out, notes
    if tavily_enabled():
        out = _eventbrite_from_search_rows(
            tavily_search("Eventbrite Chicago wedding events")
            + tavily_search("Eventbrite Milwaukee events")
            + tavily_search("Eventbrite Gary Indiana events")
        )
        if out:
            notes.append({"source": "eventbrite", "status": "ok", "count": len(out), "via": "tavily"})
            return out, notes
    if serpapi_enabled():
        out = _eventbrite_from_search_rows(
            serpapi_search("events Chicago Eventbrite", engine="google_events")
        )
        if out:
            notes.append({"source": "eventbrite", "status": "ok", "count": len(out), "via": "serpapi"})
            return out, notes
    if apify_enabled() and apify_actor("eventbrite"):
        rows = apify_run(apify_actor("eventbrite"), {"location": "Chicago", "maxItems": 40})
        out = []
        for row in rows if isinstance(rows, list) else []:
            if isinstance(row, dict):
                out.append(
                    RawEvent(
                        source="eventbrite",
                        source_url=row.get("url") or "https://www.eventbrite.com/",
                        title=row.get("name") or row.get("title"),
                        start=str(row.get("startDate") or "")[:10] or None,
                        venue=row.get("venue"),
                        text=strip_personal_contacts(str(row.get("description") or "")),
                    )
                )
        if out:
            notes.append({"source": "eventbrite", "status": "ok", "count": len(out), "via": "apify"})
            return out, notes
    notes.append(
        {
            "source": "eventbrite",
            "status": "empty",
            "detail": "public city pages (Jina/Playwright/Firecrawl) returned no /e/ links; "
            "optional TAVILY_API_KEY, SERPAPI_API_KEY, or APIFY_TOKEN",
        }
    )
    return [], notes


def parse_eventbrite_page(
    body: str, *, source_url: str, region: str | None, city: str | None
) -> list[RawEvent]:
    """Turn a city-page HTML/markdown blob into Eventbrite leads (no network)."""
    seen: set[str] = set()
    out: list[RawEvent] = []
    for match in EVENTBRITE_URL_RE.finditer(body or ""):
        url = match.group(0).split("?")[0].rstrip(").,;")
        key = url.rstrip("/").lower()
        if key in seen:
            continue
        seen.add(key)
        title = _title_from_eventbrite_url(url)
        out.append(
            RawEvent(
                source="eventbrite",
                source_url=url,
                title=title,
                city=city,
                region=region,
                text=strip_personal_contacts(title),
                extra={"page": source_url},
            )
        )
    return out


def _eventbrite_from_city_pages() -> list[RawEvent]:
    items: list[RawEvent] = []
    seen: set[str] = set()
    for url, region, city in EVENTBRITE_CITY_PAGES:
        body = fetch_public_page(url)
        if not body:
            continue
        for item in parse_eventbrite_page(body, source_url=url, region=region, city=city):
            key = item.source_url.rstrip("/").lower()
            if key in seen:
                continue
            seen.add(key)
            items.append(item)
    return items


def _eventbrite_from_search_rows(rows: list[dict]) -> list[RawEvent]:
    out: list[RawEvent] = []
    for row in rows:
        link = row.get("link") or row.get("url") or "https://www.eventbrite.com/"
        start = None
        date = row.get("date")
        if isinstance(date, dict):
            start = (date.get("start_date") or "")[:10] or None
        venue = row.get("venue")
        address = row.get("address")
        if not venue and isinstance(address, list) and address:
            venue = address[0]
        out.append(
            RawEvent(
                source="eventbrite",
                source_url=link,
                title=row.get("title"),
                start=start,
                venue=venue,
                region="chicagoland",
                text=strip_personal_contacts(
                    row.get("description") or row.get("snippet") or row.get("title") or ""
                ),
            )
        )
    return out


def _title_from_eventbrite_url(url: str) -> str:
    path = urlparse(url).path
    match = EVENTBRITE_SLUG_RE.search(path)
    slug = match.group(1) if match else path.rsplit("/", 1)[-1]
    slug = re.sub(r"-tickets$", "", slug, flags=re.I)
    words = [w for w in slug.replace("-", " ").split() if w and not w.isdigit()]
    return " ".join(words).title() if words else "Eventbrite event"


def collect_meetup() -> list[RawEvent]:
    icals = [u.strip() for u in env("MEETUP_ICAL_URLS").split(",") if u.strip()]
    items = collect_ical_urls(icals) if icals else []
    for it in items:
        it.source = "meetup"
    if items:
        return items
    if firecrawl_enabled():
        md = firecrawl_scrape("https://www.meetup.com/find/?keywords=wedding&location=us--il--chicago")
        if md:
            return [
                RawEvent(
                    source="meetup",
                    source_url="https://www.meetup.com/find/?keywords=wedding&location=us--il--chicago",
                    title="Meetup Chicago wedding search",
                    text=strip_personal_contacts(md[:2000]),
                    region="chicagoland",
                )
            ]
    return []


def collect_luma() -> tuple[list[RawEvent], list[dict]]:
    if firecrawl_enabled():
        items = []
        for url in LUMA_PAGES:
            md = firecrawl_scrape(url)
            if md:
                items.append(
                    RawEvent(
                        source="luma",
                        source_url=url,
                        title="Luma calendar",
                        text=strip_personal_contacts(md[:2000]),
                    )
                )
        if items:
            return items, []
    if apify_enabled() and apify_actor("luma"):
        rows = apify_run(apify_actor("luma"), {"startUrls": [{"url": u} for u in LUMA_PAGES]})
        items = []
        for row in rows if isinstance(rows, list) else []:
            if isinstance(row, dict):
                items.append(
                    RawEvent(
                        source="luma",
                        source_url=row.get("url") or LUMA_PAGES[0],
                        title=row.get("title") or row.get("name"),
                        start=str(row.get("start") or "")[:10] or None,
                        text=strip_personal_contacts(str(row.get("description") or "")),
                    )
                )
        return items, []
    return [], [
        {
            "source": "luma",
            "status": "skipped",
            "detail": "lu.ma is a JavaScript app; set FIRECRAWL_API_KEY or APIFY_LUMA_ACTOR",
        }
    ]


def collect_allevents() -> tuple[list[RawEvent], list[dict]]:
    # Some AllEvents city pages expose an ICS at /{city}/rss/ — try RSS/ICS first.
    items: list[RawEvent] = []
    for city in ("chicago", "milwaukee", "gary"):
        for path in (f"https://allevents.in/{city}/rss/", f"https://allevents.in/rss/{city}"):
            if not robots_allowed(path):
                continue
            try:
                body = get_text(path, timeout=20)
            except FetchError:
                continue
            if "BEGIN:VCALENDAR" in body:
                for ev in parse_ics(body):
                    items.append(
                        RawEvent(
                            source="allevents",
                            source_url=ev.get("url") or path,
                            title=ev.get("summary"),
                            start=ev.get("start"),
                            venue=ev.get("location"),
                            text=strip_personal_contacts(ev.get("description") or ev.get("summary") or ""),
                        )
                    )
            elif "<item>" in body.lower():
                for it in _rss_items(body):
                    items.append(
                        RawEvent(
                            source="allevents",
                            source_url=it.get("link") or path,
                            title=it.get("title"),
                            start=it.get("start"),
                            text=strip_personal_contacts(it.get("text") or it.get("title") or ""),
                        )
                    )
    if items:
        return items, []
    if firecrawl_enabled():
        scraped = []
        for url in ALLEVENTS_PAGES:
            md = firecrawl_scrape(url)
            if md:
                scraped.append(
                    RawEvent(
                        source="allevents",
                        source_url=url,
                        title="AllEvents listing",
                        text=strip_personal_contacts(md[:2000]),
                    )
                )
        if scraped:
            return scraped, []
    return [], [
        {
            "source": "allevents",
            "status": "skipped",
            "detail": "no public ICS/RSS at the probed URLs; set FIRECRAWL_API_KEY or APIFY_ALLEVENTS_ACTOR",
        }
    ]
