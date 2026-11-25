"""Plain-HTTPS public event calendars for the daily scanner.

Sources (no login):
  * Chicago Park District outdoor event permits, Socrata pk66-w54g (requestor names never selected)
  * Chicago DCASE special-events map, Socrata xgse-8eg7 (no applicant names)
  * Choose Chicago, Visit Milwaukee, and South Shore CVA public RSS feeds
  * Optional iCal URLs in EVENT_ICAL_URLS
  * CDOT street events from the local warehouse when it exists

Milwaukee special-event *permits* have no open dataset (probed 2026-11-25); McCormick Place's
calendar is behind a SiteGround captcha. Those paths are documented, not scraped.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from engine.collect.http import FetchError, get_json, get_text, robots_allowed
from engine.leads.event_models import RawEvent, chicago_today, iso_day, strip_personal_contacts

CHICAGO = "data.cityofchicago.org"
PARK_DATASET = "pk66-w54g"
# Requestor names are private individuals: never listed in $select (same rule as engine.warehouse DATASETS).
PARK_SELECT = (
    "organization,park_number,park_facility_name,reservation_start_date,reservation_end_date,"
    "event_type,event_description,permit_status,:created_at"
)
DCASE_DATASET = "xgse-8eg7"
DCASE_SELECT = "date,venue,venue_address,event_type,event_details,start_time,ward,location"
DENIED_PARK = frozenset({"Stage Denied", "Cancelled", "Denied"})
OPEN_PARK = frozenset({"Approved", "Issued", "Completed", "Waiting Decision", "Tentative", "On Hold"})
EVENT_TIERS = re.compile(
    r"^(Permit - Event |Permit - Festival|Permit - Corporate Event|Permit - Promotions|Venue Rental - )"
)
SOCIAL_TYPES = frozenset({"Venue Rental - Wedding", "Venue Rental - Social"})
HELD_PARK = frozenset({"Approved", "Completed", "Issued"})

RSS_FEEDS = (
    (
        "choose_chicago",
        "https://www.choosechicago.com/event/rss/",
        "Choose Chicago events RSS",
        "chicagoland",
        "Chicago",
    ),
    (
        "visit_milwaukee",
        "https://www.visitmilwaukee.org/event/rss/",
        "Visit Milwaukee events RSS",
        "milwaukee",
        "Milwaukee",
    ),
    (
        "south_shore_cva",
        "https://www.southshorecva.com/event/rss/",
        "South Shore CVA events RSS",
        "nw_indiana",
        None,
    ),
)

WINDOW_DAYS = 120


def _socrata(dataset: str, params: dict[str, str]) -> list[dict]:
    url = f"https://{CHICAGO}/resource/{dataset}.json?{urlencode(params)}"
    rows = get_json(url, timeout=90)
    if not isinstance(rows, list):
        raise FetchError(f"unexpected Socrata body for {dataset}")
    return rows


def park_row_wanted(row: dict, lo: date, hi: date) -> bool:
    """Upcoming Park District slice: open (incl. tentative/pending) event tiers and every wedding/social rental."""
    status = (row.get("permit_status") or row.get("status") or "").strip()
    if status in DENIED_PARK:
        return False
    start = _as_date(row.get("reservation_start_date") or row.get("start_date"))
    if start is None or not (lo < start <= hi):
        return False
    et = (row.get("event_type") or "").strip()
    if et in SOCIAL_TYPES:
        return True
    if EVENT_TIERS.match(et) and (not status or status in OPEN_PARK):
        return True
    return False


def collect_park_district(lo: date | None = None, hi: date | None = None) -> list[RawEvent]:
    today = lo or chicago_today()
    until = hi or (today + timedelta(days=WINDOW_DAYS))
    rows = _socrata(
        PARK_DATASET,
        {
            "$select": PARK_SELECT,
            "$where": (
                f"reservation_start_date > '{today.isoformat()}' "
                f"AND reservation_start_date <= '{until.isoformat()}T23:59:59' "
                "AND permit_status not in('Stage Denied')"
            ),
            "$limit": "50000",
            "$order": "reservation_start_date",
        },
    )
    out: list[RawEvent] = []
    for row in rows:
        if not park_row_wanted(row, today, until):
            continue
        et = (row.get("event_type") or "").strip()
        park = (row.get("park_facility_name") or "").strip() or None
        desc = (row.get("event_description") or "").strip() or None
        org = row.get("organization")
        if isinstance(org, str):
            org = org.strip()
            if org in {"", "--"}:
                org = None
        start = iso_day(row.get("reservation_start_date"))
        title = desc or (et if et in SOCIAL_TYPES else None)
        source_url = f"https://data.cityofchicago.org/d/{PARK_DATASET}"
        out.append(
            RawEvent(
                source="chicago_park_district",
                source_url=source_url,
                title=title,
                start=start,
                end=iso_day(row.get("reservation_end_date")),
                venue=park,
                city="Chicago",
                region="chicagoland",
                text=strip_personal_contacts(" · ".join(x for x in (et, desc, park, org) if x)),
                status=(row.get("permit_status") or "").strip() or None,
                host_org=org,
                extra={
                    "event_type": et,
                    "park_number": row.get("park_number"),
                    "listed": (row.get(":created_at") or "")[:10] or None,
                    "is_held": (row.get("permit_status") or "") in HELD_PARK,
                    "is_social_rental": et in SOCIAL_TYPES,
                },
            )
        )
    return out


def collect_dcase_special_events(lo: date | None = None, hi: date | None = None) -> list[RawEvent]:
    """Chicago DCASE special-events map (xgse-8eg7). No requestor/applicant field exists on this dataset."""
    today = lo or chicago_today()
    until = hi or (today + timedelta(days=WINDOW_DAYS))
    rows = _socrata(
        DCASE_DATASET,
        {
            "$select": DCASE_SELECT,
            "$where": f"date > '{today.isoformat()}' AND date <= '{until.isoformat()}'",
            "$limit": "50000",
            "$order": "date",
        },
    )
    # The map lagged on 2026-11-25 (newest row 2026-06-28). Still return whatever is in the window.
    out = []
    for row in rows:
        details = (row.get("event_details") or "").strip() or None
        venue = (row.get("venue") or row.get("venue_address") or "").strip() or None
        out.append(
            RawEvent(
                source="chicago_dcase",
                source_url=f"https://data.cityofchicago.org/d/{DCASE_DATASET}",
                title=details,
                start=iso_day(row.get("date")),
                venue=venue,
                city="Chicago",
                region="chicagoland",
                text=strip_personal_contacts(
                    " · ".join(x for x in (row.get("event_type"), details, venue, row.get("start_time")) if x)
                ),
                extra={
                    "event_type": row.get("event_type"),
                    "ward": row.get("ward"),
                    "start_time": row.get("start_time"),
                },
            )
        )
    return out


def collect_rss_calendars() -> list[RawEvent]:
    out: list[RawEvent] = []
    for source, url, label, region, city in RSS_FEEDS:
        if not robots_allowed(url):
            continue
        try:
            xml = get_text(url, timeout=40)
        except FetchError:
            continue
        for item in _rss_items(xml):
            out.append(
                RawEvent(
                    source=source,
                    source_url=item.get("link") or url,
                    title=item.get("title"),
                    start=item.get("start"),
                    venue=item.get("venue"),
                    city=city or item.get("city"),
                    region=region,
                    text=strip_personal_contacts(item.get("text") or item.get("title") or ""),
                    extra={"feed": label},
                )
            )
    return out


def collect_ical_urls(urls: list[str]) -> list[RawEvent]:
    out: list[RawEvent] = []
    for url in urls:
        url = url.strip()
        if not url or not robots_allowed(url):
            continue
        try:
            body = get_text(url, timeout=40)
        except FetchError:
            continue
        for ev in parse_ics(body):
            out.append(
                RawEvent(
                    source="ical",
                    source_url=ev.get("url") or url,
                    title=ev.get("summary"),
                    start=ev.get("start"),
                    end=ev.get("end"),
                    venue=ev.get("location"),
                    text=strip_personal_contacts(ev.get("description") or ev.get("summary") or ""),
                    extra={"calendar": url},
                )
            )
    return out


def collect_warehouse_cdot(lo: date | None = None, hi: date | None = None) -> list[RawEvent]:
    """CDOT public-way events from the DuckDB warehouse when it has been built."""
    if not Path("data/warehouse.duckdb").exists():
        return []
    try:
        from engine import db
        from engine.score.signals import q
    except ImportError:
        return []

    today = lo or chicago_today()
    until = hi or (today + timedelta(days=WINDOW_DAYS))
    con = db.connect()
    rows = q(
        con,
        f"""
        SELECT permit_no, worktype, min(start_date) AS start_d, max(end_date) AS end_d,
            first(event_key ORDER BY row_id) AS event_key,
            first(applicant_org ORDER BY row_id) FILTER (WHERE applicant_org IS NOT NULL) AS org,
            bool_or(coalesce(applicant_is_person, false)) AS person,
            first(milestone ORDER BY row_id) AS milestone,
            first(address_key ORDER BY row_id) AS address_key
        FROM street_events
        WHERE coalesce(milestone, '') NOT IN ('Cancelled', 'Denied')
          AND start_date > DATE '{today}' AND start_date <= DATE '{until}'
          AND worktype IN ('Festival', 'Parade', 'Athletic', 'Assembly', 'SideSale')
        GROUP BY permit_no, worktype
        ORDER BY start_d, permit_no
        """,
    )
    out = []
    for row in rows:
        if row["person"]:
            org = None
        else:
            org = row["org"]
        out.append(
            RawEvent(
                source="chicago_cdot",
                source_url="https://data.cityofchicago.org/d/pubx-yq2d",
                title=row["event_key"],
                start=iso_day(row["start_d"]),
                end=iso_day(row["end_d"]),
                venue=row["address_key"],
                city="Chicago",
                region="chicagoland",
                text=strip_personal_contacts(
                    " · ".join(str(x) for x in (row["worktype"], row["event_key"], org) if x)
                ),
                status=row["milestone"],
                host_org=None if row["person"] else org,
                extra={"permit_no": row["permit_no"], "worktype": row["worktype"]},
            )
        )
    return out


def _as_date(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def _rss_items(xml: str) -> list[dict[str, str | None]]:
    try:
        root = ET.fromstring(xml)
    except ET.ParseError:
        return []
    ns = {"content": "http://purl.org/rss/1.0/modules/content/"}
    items = []
    for node in root.findall(".//item"):
        title = _text(node.find("title"))
        link = _text(node.find("link"))
        desc = _text(node.find("description")) or _text(node.find("content:encoded", ns))
        start = _rss_date(node)
        items.append(
            {
                "title": title,
                "link": link,
                "text": desc,
                "start": start,
                "venue": None,
                "city": None,
            }
        )
    return items


def _rss_date(node: ET.Element) -> str | None:
    for tag in ("ev:startdate", "startdate", "pubDate", "dc:date"):
        el = (
            node.find(tag)
            if ":" not in tag
            else node.find(tag, {"ev": "http://purl.org/rss/1.0/modules/event/"})
        )
        if el is None:
            continue
        raw = (el.text or "").strip()
        if not raw:
            continue
        if re.match(r"\d{4}-\d{2}-\d{2}", raw):
            return raw[:10]
        try:
            return parsedate_to_datetime(raw).date().isoformat()
        except (TypeError, ValueError, OverflowError):
            continue
    return None


def _text(el: ET.Element | None) -> str | None:
    if el is None or el.text is None:
        return None
    text = re.sub(r"<[^>]+>", " ", el.text)
    text = re.sub(r"\s+", " ", text).strip()
    return text or None


def parse_ics(body: str) -> list[dict[str, str | None]]:
    """Minimal VEVENT reader (no third-party icalendar dependency)."""
    events: list[dict[str, str | None]] = []
    current: dict[str, str] = {}
    key = None
    for raw in body.replace("\r\n", "\n").split("\n"):
        if raw.startswith(" ") and key:
            current[key] = current.get(key, "") + raw[1:]
            continue
        if raw == "BEGIN:VEVENT":
            current = {}
            key = None
            continue
        if raw == "END:VEVENT":
            events.append(
                {
                    "summary": current.get("SUMMARY"),
                    "start": _ics_day(current.get("DTSTART")),
                    "end": _ics_day(current.get("DTEND")),
                    "location": current.get("LOCATION"),
                    "description": current.get("DESCRIPTION"),
                    "url": current.get("URL"),
                }
            )
            current = {}
            key = None
            continue
        if ":" not in raw:
            continue
        left, right = raw.split(":", 1)
        key = left.split(";", 1)[0].upper()
        current[key] = right.replace("\\n", " ").replace("\\,", ",")
    return events


def _ics_day(value: str | None) -> str | None:
    if not value:
        return None
    digits = re.sub(r"[^0-9]", "", value)
    if len(digits) >= 8:
        return f"{digits[0:4]}-{digits[4:6]}-{digits[6:8]}"
    return None


MILWAUKEE_PERMITS_NOTE = {
    "source": "milwaukee_special_event_permits",
    "status": "no_open_dataset",
    "probed": "2026-11-25",
    "open_data": "https://data.milwaukee.gov (package search 'special event' returned no permit dataset)",
    "calendar": "https://city.milwaukee.gov/dpw/administrativeservices/specialevents/calendar",
    "calendar_block": "city.milwaukee.gov robots.txt and the calendar page returned Cloudflare 403; not scraped",
    "office": "DPW Special Events, (414) 286-3915; festivals on private property (414) 286-8210",
    "records_path": (
        "Wisconsin public records (Wis. Stat. § 19.35): written request to the City of Milwaukee "
        "Department of Public Works / City Clerk records custodian for special-event permit applications "
        "and issued permits. Do not scrape the Cloudflare-protected calendar."
    ),
}

MCCORMICK_PLACE_NOTE = {
    "source": "mccormick_place_calendar",
    "status": "captcha_wall",
    "probed": "2026-11-25",
    "page": "https://www.mccormickplace.com/events/",
    "legacy": "https://mpea-web.ungerboeck.com/coe/coe_p1_all.aspx?cc=SOP-COE-FORM&oc=10",
    "note": (
        "mccormickplace.com returned a SiteGround captcha interstitial (HTTP 202) for robots.txt and /events/; "
        "the Ungerboeck calendar URL returned HTTP 500. Use FIRECRAWL_API_KEY or a session that already passed "
        "the interstitial, or copy events by hand. No fake-account or captcha-solving path is implemented."
    ),
}
