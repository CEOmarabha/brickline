"""Eventbrite, Meetup, Luma and AllEvents via feeds, official APIs, or providers."""

from __future__ import annotations

from urllib.parse import urlencode

from engine.collect.event_feeds import _rss_items, collect_ical_urls, parse_ics
from engine.collect.http import FetchError, get_json, get_text, robots_allowed
from engine.collect.social.config import env
from engine.collect.social.providers import (
    apify_actor,
    apify_enabled,
    apify_run,
    firecrawl_enabled,
    firecrawl_scrape,
    serpapi_enabled,
    serpapi_search,
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


def collect_listings() -> tuple[list[RawEvent], list[dict]]:
    items: list[RawEvent] = []
    notes: list[dict] = []
    items.extend(collect_eventbrite())
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


def collect_eventbrite() -> list[RawEvent]:
    token = env("EVENTBRITE_TOKEN")
    if token:
        url = "https://www.eventbriteapi.com/v3/events/search/?" + urlencode(
            {"location.address": "Chicago, IL", "expand": "venue", "page_size": "50"}
        )
        try:
            data = get_json(url, timeout=40, headers={"Authorization": f"Bearer {token}"})
        except FetchError:
            data = {}
        out = []
        for ev in data.get("events") or []:
            venue = (ev.get("venue") or {}).get("name")
            start = ((ev.get("start") or {}).get("local") or "")[:10] or None
            out.append(
                RawEvent(
                    source="eventbrite",
                    source_url=ev.get("url") or "https://www.eventbrite.com/",
                    title=(ev.get("name") or {}).get("text")
                    if isinstance(ev.get("name"), dict)
                    else ev.get("name"),
                    start=start,
                    venue=venue,
                    city="Chicago",
                    region="chicagoland",
                    text=strip_personal_contacts(
                        (
                            (ev.get("summary") or ev.get("description") or {}).get("text")
                            if isinstance(ev.get("description"), dict)
                            else ev.get("summary")
                        )
                        or ""
                    ),
                )
            )
        if out:
            return out
    if serpapi_enabled():
        out = []
        for row in serpapi_search("events Chicago Eventbrite", engine="google_events"):
            out.append(
                RawEvent(
                    source="eventbrite",
                    source_url=row.get("link") or "https://www.eventbrite.com/",
                    title=row.get("title"),
                    start=(row.get("date") or {}).get("start_date")
                    if isinstance(row.get("date"), dict)
                    else None,
                    venue=(row.get("address") or [None])[0]
                    if isinstance(row.get("address"), list)
                    else row.get("venue"),
                    region="chicagoland",
                    text=strip_personal_contacts(row.get("description") or row.get("title") or ""),
                )
            )
        if out:
            return out
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
        return out
    return []


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
