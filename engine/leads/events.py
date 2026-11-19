"""Upcoming-events PILOT list for an event-services business: who is running which event, with how much notice.

    uv run python -m engine.leads.events

A targeting list, not a prediction: nothing here models the chance that an organizer hires anyone. Every count, rate
and lead time is computed from the warehouse at run time. Sources: CDOT public-way event permits (`street_events`:
festivals, parades, athletic events, assemblies, sidewalk sales, block parties) and the Park District's event
reservations (`park_events`, real-event tiers only).

Groups written to web/data/events.json (the app's /pilots/events page and /export/events) and
data/events-<as-of>.csv:
  * upcoming: events starting within WINDOW_DAYS after the CDOT as-of date, with the organizer when it is an
    organization (never a person) and a conservative contact suggestion from public listings;
  * recurring: series that ran in at least 2 of the last 3 seasons, with the expected next date window and the
    historical recurrence rate (signal-lab H38 logic in engine/score/events.py);
  * block parties: resident-filed, so only the block, date, ward and community area are kept, no applicant data;
  * context: counts by type and month, lead time (review start to event start) and organization share by type.

Privacy: CDOT applicant first names are not stored, but `applicant_org` can still hold an individual's name (the
contact's last-name field). An organizer name is therefore shown only when it passes `org_status` (an organization
word, a one-word name, a known business name that does not start with a common first name, ...); anything else is
withheld and the event shows no organizer. Event names are screened the same way, and block parties never show a
name. Read-only on the warehouse; deterministic (explicit tie-breaks, rounded floats).
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

import duckdb

from engine import db
from engine.enrich.contacts import PlaceIndex, place_identity, plain_email_ok
from engine.enrich.names import GENERIC_WORDS, distinctive, normalize
from engine.leads import buyers, pest
from engine.score import events as lab
from engine.score.signals import one, q
from engine.text import title

JSON_OUT = Path("web/data/events.json")

WINDOW_DAYS = 120
RECURRING_DAYS = 365
SEASONS = 3  # twelve-month windows ending at the as-of date
MIN_SEASONS = 2
CLUSTER_GAP_DAYS = 14
IRREGULAR_DAYS = (
    lab.DATE_TOL
)  # runs in different seasons this close (after moving them a year) are one occurrence
SPREAD_FLOOR_DAYS = 7  # a series that landed on the same day every year still gets a one-week window
LEAD_FROM, LEAD_TO = "2024-01-01", "2025-12-31"
LEAD_SHARES = (14, 28, 56)
BLOCK_PARTY = "BlockParty"
CDOT_TYPES = ("Festival", "Parade", "Athletic", "Assembly", "SideSale", BLOCK_PARTY)
CDOT_EVENT_TYPES = tuple(t for t in CDOT_TYPES if t != BLOCK_PARTY)
CDOT_LABEL = {
    "Festival": "Festival",
    "Parade": "Parade",
    "Athletic": "Athletic event",
    "Assembly": "Assembly",
    "SideSale": "Sidewalk sale",
    BLOCK_PARTY: "Block party",
}
PARK_EVENT = "Park District event"
PARK_VENUE = "Park District venue rental"
PARK_VENUE_GROUP = "Venue (civic/corporate/philanthropic)"
TYPE_ORDER = (*(CDOT_LABEL[t] for t in CDOT_TYPES), PARK_EVENT, PARK_VENUE)
CLOSURE_LABEL = {
    "Full": "Full street closure",
    "Curblane": "Curb lane",
    "Sidewalk": "Sidewalk",
    "Intermitte": "Intermittent closure",
}
CDOT_STATUS = {
    "Incomplete Application": "Application incomplete",
    "Application Checks": "Application submitted",
    "Application in Review": "In City review",
    "Final Review": "Final review",
    "Final Checks": "Final review",
    "Fee Payment": "Final review",
    "Permit Active": "Permit issued",
    "Complete": "Permit issued",
}
PARK_STATUS_ORDER = ("Approved", "Issued", "Completed", "Waiting Decision", "Tentative", "On Hold")
SOURCE_CDOT = "Chicago Department of Transportation permits"
SOURCE_PARK = "Chicago Park District reservations"
SOURCE_OVERTURE = "Overture Maps"
SOURCE_LICENSES = "Chicago business licenses"
ATTRIBUTION = (
    "Events: City of Chicago open data, CDOT public-way permits and Chicago Park District reservations (not an "
    "endorsement by the City). Business listings (c) Overture Maps Foundation, CDLA-Permissive-2.0; sources include "
    "Meta and Microsoft."
)
CONTACT_NOTE = (
    "A contact suggestion is a name match between the organizer and a public business listing (Overture Maps or "
    "Chicago business licenses): exact normalized name, or a near-identical name with all differing words typo-level "
    "similar; single-word names and names shared by several businesses are never matched. It can be a different "
    "organization with the same name, so verify before use. Nothing is guessed: no email patterns, no personal "
    "contacts."
)
BLOCK_PARTY_NOTE = (
    "Block parties are filed by residents. This list shows only the block and date; the host's name and mailing "
    "address are on the Event board (/event-board). Send a letter or door hanger a few weeks before the date; call or "
    "text only a skip-traced number that passed a Do Not Call scrub (D-027)."
)
PRIVACY_NOTE = (
    "Applicants who are individuals are never stored or shown. An organizer name appears only when it looks like an "
    "organization; ambiguous names are withheld."
)

# --- organizer screen ----------------------------------------------------------------------------------------
STRONG_WORDS = frozenset(
    """LLC INC INCORPORATED CORP CORPORATION LTD LIMITED LP LLP CO COMPANY ASSOCIATION ASSOCIATES ASSN ASSO ASSOC
    CHAMBER COMMERCE CHURCH PARISH CATHEDRAL BASILICA SYNAGOGUE TEMPLE CONGREGATION MINISTRIES MINISTRY FELLOWSHIP
    SCHOOL SCHOOLS ACADEMY ACADMEY UNIVERSITY COLLEGE ELEMENTARY CAMPUS CHARTER PTA PTO PTSA FOUNDATION COUNCIL
    COMMITTEE SOCIETY SOCIETIES UNION DEPARTMENT DEPT CENTER CENTRE COMMUNITY ORGANIZATION DISTRICT CLUB CLUBS
    FEDERATION COMMISSION COALITION ALLIANCE AUTHORITY INSTITUTE MUSEUM HOSPITAL BANK LEAGUE FUND TRUST NFP CPS
    VFW LODGE LOCAL PRODUCTIONS PRESENTS ENTERTAINMENT PARTNERS PARTNERSHIP HOLDINGS ENTERPRISES MARKETING
    DEVELOPMENT BREWING BREWERY RESTAURANT RESTAURANTS HOTEL HOTELS STUDIOS NETWORK AGENCY SERVICES SOLUTIONS
    MANAGEMENT NEIGHBORHOOD NEIGHBORS BUSINESS BUSINESSES ASSEMBLY COLLECTIVE CHARITIES CHARITY SHOW FAIR""".split()
)
WEAK_WORDS = frozenset(
    """EVENTS EVENT MARKET MARKETS BAR BARS CRAWL CRAWLS RUN WALK FITNESS SPORTS SOCIAL PARK PARKS WARD FESTIVAL
    FESTIVALS GROUP PRODUCTION STUDIO MEDIA SHOP STORE GALLERY TEAM TOYS KIDS YOUTH VETERANS POST HALL PLAZA
    BUILDING TOWER CAFE BAKERY THEATER THEATRE GRILL TAVERN PUB LOUNGE BOARD PROJECT PROJECTS CITY VILLAGE CHICAGO
    CHICAGOLAND COUNTY STATE ILLINOIS""".split()
)
GEO_WORDS = frozenset(
    """SQUARE BEACH HARBOR GROVE FIELD HILL HILLS LAKE GARDEN GARDENS TERRACE HEIGHTS AVENUE STREET PLAZA RIVER
    ISLAND SOUTH NORTH EAST WEST SIDE LOOP DOWNTOWN MILE GREEN WOODS VIEW CROSSING""".split()
)
SAFE_SECOND = STRONG_WORDS | WEAK_WORDS | GEO_WORDS | GENERIC_WORDS
PERSON_TITLES = frozenset(
    """ALDERMAN ALD OFFICER COMMANDER CONGRESSMAN CONGRESSWOMAN SENATOR REPRESENTATIVE COMMISSIONER REV REVEREND
    FATHER PASTOR BISHOP DR MR MRS MS SGT""".split()
)
GOV_RX = re.compile(
    r"^(CITY OF CHICAGO|DCASE|CDOT|CHICAGO PARK DISTRICT|CHICAGO PUBLIC SCHOOLS|CPS|COOK COUNTY|STATE OF ILLINOIS|"
    r"CHICAGO POLICE|CHICAGO FIRE|CFD|CPD|WARD \d+|\d+(ST|ND|RD|TH) WARD)\b"
)
PERSONAL_EVENT_WORDS = frozenset(
    """REUNION BIRTHDAY MEMORIAL FAMILY WEDDING FUNERAL QUINCE QUINCEANERA ANNIVERSARY GATHERING COOKOUT PICNIC
    SHOWER GRADUATION PARTY""".split()
)
TEST_RX = re.compile(r"(^| )(uat|test\d*)( |$)")
ROLE_MAILBOXES = frozenset(
    """info contact hello office events admin sales support mail inquiries booking bookings marketing general
    enquiries membership volunteer volunteers programs communications press media community director""".split()
)
FIRST_NAME_MIN = 30  # a first name must be on at least this many Chicago business-owner records
SURNAME_MIN = 5
TOKEN_RX = re.compile(r"[A-Z0-9]+")


def tokens_of(name: str) -> list[str]:
    return TOKEN_RX.findall(name.upper().replace("'", ""))


class NameScreen:
    """Decides whether an applicant string may be shown as an organization (see module docstring)."""

    def __init__(self, first_names: set[str], surnames: set[str], known_keys: set[str]) -> None:
        self.first, self.sur, self.known = first_names, surnames, known_keys
        self.withheld_keys: set[str] = set()

    def person_pair(self, toks: list[str]) -> bool:
        """A common first name (optionally an initial) followed by a surname-like word."""
        for i in range(len(toks) - 1):
            j = i + 1
            if len(toks[j]) == 1 and j + 1 < len(toks):
                j += 1
            if toks[i] in self.first and toks[j] in self.sur and toks[j] not in SAFE_SECOND:
                return True
        return False

    def org_status(self, name: str) -> str:
        """'organization', 'government' or 'withheld'."""
        toks = tokens_of(name)
        if not toks or not name.isascii() or any(c in name for c in "/()") or PERSON_TITLES & set(toks):
            return "withheld"
        up = " ".join(toks)
        if GOV_RX.match(up):
            return "government"
        if STRONG_WORDS & set(toks):
            return "organization"
        if toks[0].isdigit():
            return "withheld"
        if len(toks) == 1:
            return "organization" if len(toks[0]) >= 2 else "withheld"
        if self.person_pair(toks) or (toks[0] in self.first and len(toks) <= 4):
            return "withheld"
        if normalize(name) in self.known or WEAK_WORDS & set(toks):
            return "organization"
        return "organization" if len(toks) >= 5 and "&" not in name else "withheld"

    def event_name_ok(self, key: str | None, organizer_known: bool = False) -> bool:
        """An event name may be shown when it does not read as a person's name; with an organization organizer the
        first-name-plus-surname check is skipped (the name is then most likely the organization's own event)."""
        if not key:
            return False
        toks = tokens_of(key)
        if not toks or PERSON_TITLES & set(toks) or normalize(key) in self.withheld_keys:
            return False
        if organizer_known:
            return True
        return not (
            self.person_pair(toks)
            or PERSONAL_EVENT_WORDS & set(toks)
            or "S" in toks
            or (toks[0] in self.first and len(toks) <= 3)
            or (len(toks) == 1 and toks[0] in self.sur)
            or any(a == "TEAM" and b in self.sur for a, b in zip(toks, toks[1:], strict=False))
        )


def rnd(x: float | None, digits: int = 4) -> float | None:
    return None if x is None else round(float(x), digits)


def pretty(name: str) -> str:
    """Display form of a record name: all-caps and all-lowercase names are title-cased, short acronyms kept."""
    name = re.sub(r"[%*#]+$", "", name.strip()).strip()
    if re.fullmatch(r"[A-Z0-9]{2,6}", name):
        return name
    return title(name) if name.isupper() or name.islower() else name


def add_years(d: date, years: int) -> date:
    try:
        return d.replace(year=d.year + years)
    except ValueError:
        return d.replace(year=d.year + years, day=28)


def season_of(d: date, asof: date) -> int:
    """1 = the twelve months ending at the as-of date, 2 = the twelve months before that, ..."""
    return max(1, -(-(asof - d).days // 365))


def block_text(address_key: str | None) -> str | None:
    """'1234 W CERMAK RD' -> '1200 block of W Cermak Rd' (a block, never a house number)."""
    if not address_key:
        return None
    m = re.match(r"^(\d+)\s+(.+)$", address_key)
    if not m:
        return title(address_key)
    return f"{int(m.group(1)) // 100 * 100} block of {title(m.group(2))}"


def street_text(address_key: str | None) -> str | None:
    return title(address_key) if address_key else None


# ----------------------------------------------------------------------------------------------------------
# Tables
# ----------------------------------------------------------------------------------------------------------
def load_name_sets(con: duckdb.DuckDBPyConnection) -> tuple[set[str], set[str]]:
    """Common given names and surnames among Chicago business-license owner records, used only to recognise
    individuals' names; never written anywhere."""
    first = {
        r[0]
        for r in con.execute(
            f"SELECT first_name FROM biz_owners WHERE length(first_name) >= 3 GROUP BY 1 HAVING count(*) >= {FIRST_NAME_MIN}"
        ).fetchall()
    }
    sur = {
        r[0]
        for r in con.execute(
            f"SELECT last_name FROM biz_owners WHERE last_name IS NOT NULL GROUP BY 1 HAVING count(*) >= {SURNAME_MIN}"
        ).fetchall()
    }
    return first, sur


def load_places(con: duckdb.DuckDBPyConnection) -> tuple[list[dict], str]:
    rows = q(
        con,
        """
        SELECT id, name, category, phones, websites, emails, address, locality, postcode, confidence, release
        FROM places
        WHERE in_chicago AND status IS DISTINCT FROM 'permanently_closed' AND name IS NOT NULL ORDER BY id
    """,
    )
    for r in rows:
        r["in_chicago"] = True
    return rows, rows[0]["release"] if rows else ""


def build_org_table(con: duckdb.DuckDBPyConnection, screen: NameScreen) -> dict[str, str]:
    """Temp table org_ok(name, key, status) over every applicant organization string; returns name -> status."""
    names = sorted(
        {
            r[0]
            for r in con.execute(
                "SELECT DISTINCT applicant_org FROM street_events WHERE applicant_org IS NOT NULL "
                "UNION SELECT DISTINCT organization FROM park_events WHERE organization IS NOT NULL"
            ).fetchall()
        }
    )
    status = {n: screen.org_status(n) for n in names}
    screen.withheld_keys = {normalize(n) for n, s in status.items() if s == "withheld"} - {""}
    con.execute("CREATE OR REPLACE TEMP TABLE org_ok (name VARCHAR, key VARCHAR, status VARCHAR)")
    con.executemany("INSERT INTO org_ok VALUES (?, ?, ?)", [(n, normalize(n), s) for n, s in status.items()])
    return status


def build_cdot(con: duckdb.DuckDBPyConnection, asof: date) -> None:
    """Temp table cdot: one row per CDOT permit and work type (not cancelled or denied); the primary segment is the
    first row by row_id."""
    types = ", ".join(f"'{t}'" for t in CDOT_TYPES)
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE cdot AS
        SELECT permit_no, worktype,
            min(start_date) AS start_d, max(end_date) AS end_d, min(processed_date) AS processed,
            min(issue_date) AS issued, first(milestone ORDER BY row_id) AS milestone,
            bool_or(coalesce(applicant_is_person, false)) AS person,
            first(applicant_org ORDER BY row_id) FILTER (WHERE applicant_org IS NOT NULL) AS org,
            first(event_key ORDER BY row_id) FILTER (WHERE event_key IS NOT NULL) AS event_key,
            first(address_key ORDER BY row_id) AS address_key, count(DISTINCT address_key) AS segments,
            string_agg(DISTINCT closure, ',' ORDER BY closure) AS closures,
            first(ward ORDER BY row_id) AS ward,
            first(lat ORDER BY row_id) FILTER (WHERE lat IS NOT NULL AND lon IS NOT NULL) AS lat,
            first(lon ORDER BY row_id) FILTER (WHERE lat IS NOT NULL AND lon IS NOT NULL) AS lon
        FROM street_events
        WHERE coalesce(milestone, '') NOT IN ('Cancelled', 'Denied') AND start_date IS NOT NULL
          AND worktype IN ({types}) AND start_date <= DATE '{asof}' + {RECURRING_DAYS + 31}
        GROUP BY permit_no, worktype
    """)
    con.execute("INSTALL spatial; LOAD spatial;")
    con.execute("""
        CREATE OR REPLACE TEMP TABLE ca_geom AS
        SELECT community_area, name, ST_GeomFromText(geom_wkt) AS geom FROM community_areas
    """)
    con.execute("""
        CREATE OR REPLACE TEMP TABLE cdot_ca AS
        SELECT c.permit_no, c.worktype, min(g.community_area) AS community_area, min(g.name) AS area_name
        FROM cdot c JOIN ca_geom g ON c.lat IS NOT NULL AND ST_Contains(g.geom, ST_Point(c.lon, c.lat))
        GROUP BY 1, 2
    """)


def cdot_rows(con: duckdb.DuckDBPyConnection, where: str) -> list[dict]:
    return q(
        con,
        f"""
        SELECT c.permit_no, c.worktype, c.start_d, c.end_d, c.processed, c.issued, c.milestone, c.person, c.org,
            c.event_key, c.address_key, c.segments, c.closures, c.ward, a.community_area, a.area_name,
            coalesce(o.status, 'none') AS org_status, o.key AS org_key
        FROM cdot c LEFT JOIN cdot_ca a USING (permit_no, worktype) LEFT JOIN org_ok o ON o.name = c.org
        WHERE ({where}) AND NOT regexp_matches(coalesce(c.event_key, ''), '{TEST_RX.pattern}')
        ORDER BY c.start_d, c.worktype, c.permit_no
    """,
    )


def organizer_fields(row: dict) -> dict:
    """Organizer columns of a CDOT row (never a person)."""
    if row["person"]:
        return {"organizer": None, "organizerIsPerson": True, "organizerStatus": "individual", "kind": None}
    st = row["org_status"]
    if st in ("organization", "government"):
        return {
            "organizer": pretty(row["org"]),
            "organizerIsPerson": False,
            "organizerStatus": "organization",
            "kind": "public agency" if st == "government" else None,
        }
    if st == "withheld":
        return {"organizer": None, "organizerIsPerson": True, "organizerStatus": "withheld", "kind": None}
    return {"organizer": None, "organizerIsPerson": None, "organizerStatus": "unpublished", "kind": None}


def closure_text(closures: str | None) -> str | None:
    parts = [CLOSURE_LABEL[c] for c in (closures or "").split(",") if c in CLOSURE_LABEL]
    return ", ".join(parts) or None


def cdot_event(row: dict, asof: date, screen: NameScreen) -> dict:
    org = organizer_fields(row)
    name_ok = row["worktype"] != BLOCK_PARTY and screen.event_name_ok(
        row["event_key"], bool(org["organizer"])
    )
    return {
        "id": f"cdot-{row['permit_no']}-{row['worktype'].lower()}",
        "source": SOURCE_CDOT,
        "type": CDOT_LABEL[row["worktype"]],
        "name": title(row["event_key"]) if name_ok else None,
        "startDate": row["start_d"].isoformat(),
        "endDate": (
            row["end_d"] if row["end_d"] and row["end_d"] >= row["start_d"] else row["start_d"]
        ).isoformat(),
        "daysUntil": (row["start_d"] - asof).days,
        "location": street_text(row["address_key"]),
        "segments": row["segments"],
        "closure": closure_text(row["closures"]),
        "communityArea": {"id": row["community_area"], "name": row["area_name"]}
        if row["community_area"]
        else None,
        "ward": row["ward"],
        **org,
        "status": CDOT_STATUS.get(row["milestone"], row["milestone"]),
        "firstSeen": row["processed"].isoformat() if row["processed"] else None,
        "contact": None,
        "_org_key": row["org_key"],
        "_org_status": row["org_status"],
    }


def park_rows(con: duckdb.DuckDBPyConnection, lo: date, hi: date) -> list[dict]:
    return q(
        con,
        f"""
        SELECT p.event_key, p.grp, coalesce(p.park_no::VARCHAR, 'n:' || p.park_name) AS pk, p.park_name, p.start_date,
            p.end_date, p.status, p.is_held,
            p.listed_date, p.organization, coalesce(o.status, 'none') AS org_status, o.key AS org_key
        FROM park_events p LEFT JOIN org_ok o ON o.name = p.organization
        WHERE p.is_real AND p.event_key IS NOT NULL AND coalesce(p.status, '') <> 'Stage Denied'
          AND p.start_date > DATE '{lo}' AND p.start_date <= DATE '{hi}'
          AND (p.grp LIKE 'Event %' OR (p.grp = '{PARK_VENUE_GROUP}' AND o.status IN ('organization', 'government')))
        ORDER BY p.start_date, p.event_key, p.park_name, p.status
    """,
    )


def park_events_from(rows: list[dict], asof: date, screen: NameScreen) -> list[dict]:
    """One event per (event key, tier, start month); the facility shown is the first by name."""
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for r in rows:
        groups[(r["event_key"], r["grp"], r["start_date"].strftime("%Y-%m"))].append(r)
    out = []
    for (key, grp, month), rs in sorted(groups.items()):
        org_rows = [r for r in rs if r["org_status"] in ("organization", "government")]
        org_row = min(org_rows, key=lambda r: r["organization"]) if org_rows else None
        withheld = any(r["org_status"] == "withheld" for r in rs)
        statuses = {r["status"] for r in rs}
        status = next((s for s in PARK_STATUS_ORDER if s in statuses), sorted(statuses)[0])
        facilities = sorted({r["park_name"] for r in rs if r["park_name"]})
        start = min(r["start_date"] for r in rs)
        end = max(r["end_date"] or r["start_date"] for r in rs)
        if end < start or (end - start).days > 120:
            end = max(r["start_date"] for r in rs)
        listed = [r["listed_date"] for r in rs if r["listed_date"]]
        if org_row:
            organizer, is_person, st = pretty(org_row["organization"]), False, "organization"
            kind = "public agency" if org_row["org_status"] == "government" else None
        elif withheld:
            organizer, is_person, st, kind = None, True, "withheld", None
        else:
            organizer, is_person, st, kind = None, None, "unpublished", None
        digest = hashlib.md5(f"{key}|{grp}|{month}".encode()).hexdigest()[:10]  # noqa: S324 (id only)
        out.append(
            {
                "id": f"park-{digest}",
                "source": SOURCE_PARK,
                "type": PARK_VENUE if grp == PARK_VENUE_GROUP else PARK_EVENT,
                "tier": None if grp == PARK_VENUE_GROUP else grp,
                "name": title(key) if screen.event_name_ok(key, bool(organizer)) else None,
                "startDate": start.isoformat(),
                "endDate": end.isoformat(),
                "daysUntil": (start - asof).days,
                "location": facilities[0] if facilities else None,
                "segments": len(facilities),
                "closure": None,
                "communityArea": None,
                "ward": None,
                "organizer": organizer,
                "organizerIsPerson": is_person,
                "organizerStatus": st,
                "kind": kind,
                "status": status,
                "firstSeen": min(listed).isoformat() if listed else None,
                "contact": None,
                "_org_key": org_row["org_key"] if org_row else None,
                "_org_status": org_row["org_status"] if org_row else "none",
            }
        )
    return out


# ----------------------------------------------------------------------------------------------------------
# Contact suggestions (public listings, name match only)
# ----------------------------------------------------------------------------------------------------------
class Contacts:
    def __init__(self, con: duckdb.DuckDBPyConnection, places: list[dict]) -> None:
        self.idx = PlaceIndex(places)
        self.cache: dict[str, dict | None] = {}
        rows = q(
            con,
            """
            SELECT account_number, site_number, legal_name, dba, address, address_key, zip
            FROM biz_licenses ORDER BY account_number, site_number, license_id
        """,
        )
        self.lic: dict[str, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
        for r in rows:
            for n in (r["legal_name"], r["dba"]):
                k = normalize(n)
                if k and r not in self.lic[k][r["account_number"]]:
                    self.lic[k][r["account_number"]].append(r)

    def place(self, key: str) -> tuple[dict, str] | None:
        toks = key.split()
        if len(toks) < 2 or not distinctive(key):
            return None
        method, hits = "exact", self.idx.exact.get(key, [])
        if not hits:
            method, hits = "similar", self.idx.fuzzy(key)
        pool = [self.idx.rows[i] for i in hits]
        if not pool or len({place_identity(p) for p in pool}) > 1:
            return None
        best = sorted(
            pool, key=lambda p: (not p["websites"], not p["phones"], -(p["confidence"] or 0), p["id"])
        )[0]
        return best, method

    def license(self, key: str) -> dict | None:
        if len(key.split()) < 2 or not distinctive(key):
            return None
        accounts = self.lic.get(key)
        if not accounts or len(accounts) != 1:
            return None
        rows = next(iter(accounts.values()))
        if len({r["address_key"] for r in rows}) != 1 or not rows[0]["address"]:
            return None
        r = rows[0]
        return {
            "address": ", ".join(
                x
                for x in (title(r["address"]), f"Chicago IL {r['zip'][:5]}" if r["zip"] else "Chicago IL")
                if x
            )
        }

    def suggest(self, key: str) -> dict | None:
        if key in self.cache:
            return self.cache[key]
        place, lic = self.place(key), self.license(key)
        out = None
        if place:
            p, method = place
            out = {
                "name": pretty(p["name"]),
                "phone": pest.phone_of(p["phones"]),
                "website": buyers.usable_site(p["websites"]),
                "email": role_email(p["emails"]),
                "address": ", ".join(x for x in (p["address"], p["locality"], p["postcode"]) if x) or None,
                "source": SOURCE_OVERTURE,
                "match": method,
                "alsoIn": [SOURCE_LICENSES] if lic else [],
            }
        elif lic:
            out = {
                "name": None,
                "phone": None,
                "website": None,
                "email": None,
                "address": lic["address"],
                "source": SOURCE_LICENSES,
                "match": "exact",
                "alsoIn": [],
            }
        self.cache[key] = out
        return out


def role_email(values) -> str | None:
    """First listed email that is a role mailbox (info@, events@, ...); an address that looks personal is dropped."""
    for v in values or []:
        mail = (v or "").strip().lower()
        if "@" in mail and mail.split("@")[0] in ROLE_MAILBOXES and plain_email_ok(mail):
            return mail
    return None


def has_details(c: dict | None) -> bool:
    return bool(c and (c["phone"] or c["website"] or c["email"]))


def attach_contacts(items: list[dict], contacts: Contacts) -> None:
    for e in items:
        key = e.get("_org_key")
        if e["organizer"] and key and e.get("_org_status") == "organization":
            e["contact"] = contacts.suggest(key)


def contact_stats(items: list[dict]) -> dict:
    """Distinct organizers (by normalized name) that are not public agencies, and how many got a suggestion."""
    orgs: dict[str, dict | None] = {}
    for e in items:
        if e["organizer"] and e.get("_org_status") == "organization" and e.get("_org_key"):
            orgs[e["_org_key"]] = e["contact"]
    n = len(orgs)
    any_c = sum(1 for c in orgs.values() if c)
    det = sum(1 for c in orgs.values() if has_details(c))
    return {
        "organizations": n,
        "withSuggestion": any_c,
        "withPhoneWebsiteOrEmail": det,
        "suggestionShare": rnd(any_c / n if n else None),
        "detailsShare": rnd(det / n if n else None),
    }


def strip_private(items: list[dict]) -> None:
    for e in items:
        e.pop("_org_key", None)
        e.pop("_org_status", None)


# ----------------------------------------------------------------------------------------------------------
# Recurring series
# ----------------------------------------------------------------------------------------------------------
def series_key_cdot(r: dict) -> str | None:
    """Named events: event name + organization (or + ward when no organization); unnamed: organization + ward."""
    org = r["org_key"] if not r["person"] and r["org_status"] in ("organization", "government") else None
    if r["event_key"]:
        return f"n|{r['event_key']}|{org or '~' + str(r['ward'])}"
    return f"u|{org}|{r['ward']}" if org else None


def median_ordinal(values: list[int]) -> int:
    v = sorted(values)
    return v[len(v) // 2] if len(v) % 2 else (v[len(v) // 2 - 1] + v[len(v) // 2]) // 2


def season_runs(spans: list[tuple[date, date | None]], asof: date) -> list[tuple[int, date, date]]:
    """(season, start, end) of each run of dates: dates less than CLUSTER_GAP_DAYS apart chain into one run, so a
    series that meets weekly for a month is one run."""
    by: dict[int, list[tuple[date, date]]] = defaultdict(list)
    for s, e in spans:
        k = season_of(s, asof)
        if k <= SEASONS:
            by[k].append((s, e if e and s <= e <= s + timedelta(days=120) else s))
    runs = []
    for k, v in sorted(by.items()):
        v.sort()
        start, end = v[0]
        for s, e in v[1:]:
            if (s - end).days > CLUSTER_GAP_DAYS:
                runs.append((k, start, end))
                start, end = s, e
            else:
                end = max(end, e)
        runs.append((k, start, end))
    return runs


def recurring_occurrences(spans: list[tuple[date, date | None]], asof: date) -> list[dict]:
    """Expected next windows of one series. Each run is moved forward by its season's age in years; shifted runs
    within IRREGULAR_DAYS of each other are the same yearly occurrence, and an occurrence needs runs in at least
    MIN_SEASONS different seasons. The window is the median shifted start plus or minus the largest deviation
    (at least SPREAD_FLOOR_DAYS)."""
    shifted = sorted(
        (add_years(s, k).toordinal(), add_years(e, k).toordinal(), k, s)
        for k, s, e in season_runs(spans, asof)
    )
    clusters: list[list[tuple[int, int, int, date]]] = []
    for item in shifted:
        if clusters and item[0] - clusters[-1][-1][0] <= IRREGULAR_DAYS:
            clusters[-1].append(item)
        else:
            clusters.append([item])
    out = []
    for cl in clusters:
        seasons = sorted({k for _, _, k, _ in cl})
        if len(seasons) < MIN_SEASONS:
            continue
        center = median_ordinal([o for o, _, _, _ in cl])
        end_c = max(median_ordinal([e for _, e, _, _ in cl]), center)
        half = max(max(abs(o - center) for o, _, _, _ in cl), SPREAD_FLOOR_DAYS)
        c = date.fromordinal(center)
        if not (asof < c <= asof + timedelta(days=RECURRING_DAYS)):
            continue
        out.append(
            {
                "seasonsRun": len(seasons),
                "yearsRun": sorted({d.year for _, _, _, d in cl}),
                "lastDate": max(d for _, _, _, d in cl).isoformat(),
                "ranLastSeason": seasons[0] == 1,
                "consecutive": len(seasons) == SEASONS
                or (len(seasons) == 2 and seasons[1] - seasons[0] == 1),
                "typicalStart": c.strftime("%m-%d"),
                "typicalEnd": date.fromordinal(end_c).strftime("%m-%d"),
                "expectedStart": date.fromordinal(center - half).isoformat(),
                "expectedEnd": date.fromordinal(center + half).isoformat(),
                "spreadDays": half,
                "daysUntilExpected": (c - asof).days,
            }
        )
    return out


def on_calendar(occ: dict, filed: list[date]) -> bool:
    """A permit or reservation for the same series already falls in (or within a month of) the expected window."""
    lo = date.fromisoformat(occ["expectedStart"]) - timedelta(days=IRREGULAR_DAYS)
    hi = date.fromisoformat(occ["expectedEnd"]) + timedelta(days=IRREGULAR_DAYS)
    return any(lo <= d <= hi for d in filed)


def series_id(key: str, occ: dict) -> str:
    return "series-" + hashlib.md5(f"{key}|{occ['typicalStart']}".encode()).hexdigest()[:10]  # noqa: S324 (id only)


def recurring_series(
    con: duckdb.DuckDBPyConnection,
    asof: date,
    screen: NameScreen,
    upcoming_dates: dict[str, list[date]],
    rates: dict,
) -> list[dict]:
    lo = asof - timedelta(days=365 * SEASONS)
    large = ", ".join(f"'{t}'" for t in lab.CDOT_LARGE)
    held = cdot_rows(
        con,
        f"c.worktype IN ({large}) AND c.milestone = 'Complete' AND c.start_d > DATE '{lo}' AND c.start_d <= DATE '{asof}'",
    )
    groups: dict[str, list[dict]] = defaultdict(list)
    for r in held:
        k = series_key_cdot(r)
        if k:
            groups[k].append(r)
    out = []
    for key, rs in sorted(groups.items()):
        occs = recurring_occurrences([(r["start_d"], r["end_d"]) for r in rs], asof)
        if not occs:
            continue
        newest = sorted(rs, key=lambda r: (r["start_d"], r["permit_no"]), reverse=True)
        last = newest[0]
        src = next((r for r in newest if organizer_fields(r)["organizer"]), last)
        org = organizer_fields(src)
        name = (
            title(last["event_key"])
            if last["event_key"] and screen.event_name_ok(last["event_key"], bool(org["organizer"]))
            else None
        )
        if not (org["organizer"] or name):
            continue
        for occ in occs:
            out.append(
                {
                    "id": series_id(key, occ),
                    "source": SOURCE_CDOT,
                    "type": CDOT_LABEL[last["worktype"]],
                    "name": name,
                    "organizer": org["organizer"],
                    "organizerIsPerson": org["organizerIsPerson"],
                    "organizerStatus": org["organizerStatus"],
                    "kind": org["kind"],
                    "location": street_text(last["address_key"]),
                    "segments": last["segments"],
                    "communityArea": {"id": last["community_area"], "name": last["area_name"]}
                    if last["community_area"]
                    else None,
                    "ward": last["ward"],
                    "contact": None,
                    "_org_key": src["org_key"] if org["organizer"] else None,
                    "_org_status": src["org_status"] if org["organizer"] else "none",
                    "_rate_kind": "cdotNamed" if last["event_key"] else "cdotUnnamed",
                    "_group": last["worktype"],
                    "_series": key,
                    **occ,
                }
            )
    out.extend(park_recurring(con, asof, screen))
    for s in out:
        kind, group = s.pop("_rate_kind"), s.pop("_group")
        # The lab's rates are for series held in each of the last 2 (3) years; a lapsed or gapped series is not comparable.
        s["recurrence"] = (
            rate_for(rates, kind, group, s["seasonsRun"]) if s["consecutive"] and s["ranLastSeason"] else None
        )
        s["onCalendar"] = on_calendar(s, upcoming_dates.get(s.pop("_series"), []))
    return sorted(out, key=lambda s: (s["expectedStart"], s["daysUntilExpected"], s["id"]))


def park_recurring(con: duckdb.DuckDBPyConnection, asof: date, screen: NameScreen) -> list[dict]:
    lo = asof - timedelta(days=365 * SEASONS)
    rows = q(
        con,
        f"""
        SELECT p.event_key, p.grp, coalesce(p.park_no::VARCHAR, 'n:' || p.park_name) AS pk, p.park_name, p.start_date,
            p.end_date, p.organization, coalesce(o.status, 'none') AS org_status, o.key AS org_key
        FROM park_events p LEFT JOIN org_ok o ON o.name = p.organization
        WHERE p.is_real AND p.is_held AND p.event_key IS NOT NULL AND p.start_date > DATE '{lo}'
          AND p.start_date <= DATE '{asof}'
          AND (p.grp LIKE 'Event %' OR (p.grp = '{PARK_VENUE_GROUP}' AND o.status IN ('organization', 'government')))
        ORDER BY p.start_date, p.event_key, pk, p.park_name
    """,
    )
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for r in rows:
        groups[(r["event_key"], r["pk"])].append(r)
    out = []
    for (key, pk), rs in sorted(groups.items()):
        occs = recurring_occurrences([(r["start_date"], r["end_date"]) for r in rs], asof)
        if not occs:
            continue
        last = max(rs, key=lambda r: (r["start_date"], r["park_name"] or ""))
        org_row = next((r for r in reversed(rs) if r["org_status"] in ("organization", "government")), None)
        organizer = pretty(org_row["organization"]) if org_row else None
        name = title(key) if screen.event_name_ok(key, bool(organizer)) else None
        if not organizer and not name:
            continue
        withheld = any(r["org_status"] == "withheld" for r in rs)
        grp = last["grp"]
        for occ in occs:
            out.append(
                {
                    "id": series_id(f"park|{key}|{pk}", occ),
                    "source": SOURCE_PARK,
                    "type": PARK_VENUE if grp == PARK_VENUE_GROUP else PARK_EVENT,
                    "name": name,
                    "organizer": organizer,
                    "organizerIsPerson": False if organizer else (True if withheld else None),
                    "organizerStatus": "organization"
                    if organizer
                    else ("withheld" if withheld else "unpublished"),
                    "kind": "public agency" if org_row and org_row["org_status"] == "government" else None,
                    "location": last["park_name"],
                    "segments": 1,
                    "communityArea": None,
                    "ward": None,
                    "contact": None,
                    "_org_key": org_row["org_key"] if org_row else None,
                    "_org_status": org_row["org_status"] if org_row else "none",
                    "_rate_kind": "park",
                    "_group": grp,
                    "_series": f"park|{key}|{pk}",
                    **occ,
                }
            )
    return out


def recurrence_rates(con: duckdb.DuckDBPyConnection, asof: date) -> dict:
    """Recurrence rates by history length from the signal-lab series logic (engine/score/events.py)."""
    large = ", ".join(f"'{t}'" for t in lab.CDOT_LARGE)
    kinds = {
        "cdotNamed": ("CDOT events with an event name (series = name and ward)", lab.cdot_series_src()),
        "cdotUnnamed": (
            "CDOT events without a name, filed by an organization (series = organization and ward)",
            f"""SELECT o.key AS k, coalesce(s.ward::VARCHAR, '?') AS pk, s.start_date AS d, s.worktype AS grp,
                   true AS has_org
               FROM street_events s JOIN org_ok o ON o.name = s.applicant_org AND o.status <> 'withheld'
               WHERE s.worktype IN ({large}) AND s.milestone = 'Complete' AND s.event_key IS NULL
                 AND NOT coalesce(s.applicant_is_person, false)""",
        ),
        "park": ("Park District real events (series = event name and park)", lab.park_series_src()),
    }
    out = {}
    for kind, (label, src) in kinds.items():
        lab.build_series(con, kind, src, asof.isoformat())
        m = lab.series_metrics(con, kind, asof.isoformat())
        rules = {r["rule"]: r for r in m["by_rule"]}
        two = rules.get("held in each of the last 2 years")
        three = rules.get("held in each of the last 3 years")
        out[kind] = {
            "label": label,
            "heldTwo": {
                "series": two["series_years"],
                "hits": two["hits"],
                "rate": rnd(two["precision_rate"]),
            }
            if two
            else None,
            "heldThree": {
                "series": three["series_years"],
                "hits": three["hits"],
                "rate": rnd(three["precision_rate"]),
            }
            if three
            else None,
            "debut": next(
                (
                    {"series": r["series_years"], "hits": r["hits"], "rate": rnd(r["precision_rate"])}
                    for r in m["by_rule"]
                    if r["rule"].startswith("debut")
                ),
                None,
            ),
            "byGroup": [
                {
                    "group": g["group"],
                    "heldTwoSeries": g["held2_n"],
                    "heldTwoRate": rnd(g["held2_rate"]),
                    "heldThreeSeries": g["held3_n"],
                    "heldThreeRate": rnd(g["held3_rate"]),
                }
                for g in m["by_group"]
            ],
            "dateStability": {
                "series": m["date_stability"]["n"],
                "within7DaysShare": rnd(m["date_stability"]["within_7_days_share"]),
                "within31DaysShare": rnd(m["date_stability"]["within_31_days_share"]),
            },
        }
    return out


def rate_for(rates: dict, kind: str, group: str, seasons: int) -> dict | None:
    """The rate for series with this history length: the group's own rate when it has enough series, else pooled."""
    r = rates[kind]
    length = 3 if seasons >= 3 else 2
    pooled = r["heldThree"] if length == 3 else r["heldTwo"]
    own = next((g for g in r["byGroup"] if g["group"] == group), None)
    n_key, r_key = ("heldThreeSeries", "heldThreeRate") if length == 3 else ("heldTwoSeries", "heldTwoRate")
    if own and own[r_key] is not None:
        return {"rate": own[r_key], "series": own[n_key], "years": length, "scope": group}
    if pooled and pooled["rate"] is not None:
        return {"rate": pooled["rate"], "series": pooled["series"], "years": length, "scope": "all"}
    return None


# ----------------------------------------------------------------------------------------------------------
# Block parties and context
# ----------------------------------------------------------------------------------------------------------
def block_parties(con: duckdb.DuckDBPyConnection, asof: date) -> dict:
    hi = asof + timedelta(days=WINDOW_DAYS)
    rows = cdot_rows(
        con, f"c.worktype = '{BLOCK_PARTY}' AND c.start_d > DATE '{asof}' AND c.start_d <= DATE '{hi}'"
    )
    items = []
    for r in rows:
        end = r["end_d"] if r["end_d"] and r["end_d"] >= r["start_d"] else r["start_d"]
        items.append(
            {
                "id": f"cdot-{r['permit_no']}-blockparty",
                "startDate": r["start_d"].isoformat(),
                "endDate": end.isoformat(),
                "daysUntil": (r["start_d"] - asof).days,
                "block": block_text(r["address_key"]),
                "segments": r["segments"],
                "closure": closure_text(r["closures"]),
                "ward": r["ward"],
                "communityArea": {"id": r["community_area"], "name": r["area_name"]}
                if r["community_area"]
                else None,
                "status": CDOT_STATUS.get(r["milestone"], r["milestone"]),
            }
        )
    items.sort(key=lambda x: (x["startDate"], x["block"] or "", x["id"]))
    by_area: dict[tuple, int] = defaultdict(int)
    by_week: dict[int, int] = defaultdict(int)
    for it in items:
        ca = it["communityArea"]
        by_area[(ca["id"], ca["name"]) if ca else (0, "Area not located")] += 1
        by_week[(it["daysUntil"] - 1) // 7] += 1
    weeks = [
        {
            "weekStart": (asof + timedelta(days=1 + 7 * i)).isoformat(),
            "parties": by_week.get(i, 0),
        }
        for i in range((WINDOW_DAYS + 6) // 7)
    ]
    areas = [
        {"id": a, "name": n, "parties": c}
        for (a, n), c in sorted(by_area.items(), key=lambda kv: (-kv[1], kv[0][1], kv[0][0]))
    ]
    return {"note": BLOCK_PARTY_NOTE, "total": len(items), "byArea": areas, "byWeek": weeks, "items": items}


def month_range(lo: date, hi: date) -> list[str]:
    out, d = [], date(lo.year, lo.month, 1)
    while d <= hi:
        out.append(d.strftime("%Y-%m"))
        d = date(d.year + (d.month == 12), d.month % 12 + 1, 1)
    return out


def context(
    con: duckdb.DuckDBPyConnection, asof: date, upcoming: list[dict], upcoming_cdot: list[dict]
) -> dict:
    past_lo = asof - timedelta(days=365)
    hi = asof + timedelta(days=WINDOW_DAYS)
    past_cdot = cdot_rows(con, f"c.start_d > DATE '{past_lo}' AND c.start_d <= DATE '{asof}'")
    past_park = q(
        con,
        f"""
        SELECT p.event_key, p.grp, strftime(p.start_date, '%Y-%m') AS month, any_value(p.park_no) AS park_no,
            max(coalesce(o.status, 'none') IN ('organization', 'government')::INT) AS has_org
        FROM park_events p LEFT JOIN org_ok o ON o.name = p.organization
        WHERE p.is_real AND p.is_held AND p.event_key IS NOT NULL
          AND p.start_date > DATE '{past_lo}' AND p.start_date <= DATE '{asof}'
          AND (p.grp LIKE 'Event %' OR (p.grp = '{PARK_VENUE_GROUP}' AND o.status IN ('organization', 'government')))
        GROUP BY p.event_key, p.grp, strftime(p.start_date, '%Y-%m')
    """,
    )
    past: dict[tuple[str, str], int] = defaultdict(int)
    for r in past_cdot:
        past[(r["start_d"].strftime("%Y-%m"), CDOT_LABEL[r["worktype"]])] += 1
    for r in past_park:
        past[(r["month"], PARK_VENUE if r["grp"] == PARK_VENUE_GROUP else PARK_EVENT)] += 1
    nxt: dict[tuple[str, str], int] = defaultdict(int)
    for e in upcoming_cdot:
        nxt[(e["startDate"][:7], e["type"])] += 1
    for e in upcoming:
        if e["source"] == SOURCE_PARK:
            nxt[(e["startDate"][:7], e["type"])] += 1

    def table(counts: dict, months: list[str]) -> list[dict]:
        rows = []
        for m in months:
            by = {t: counts.get((m, t), 0) for t in TYPE_ORDER}
            rows.append({"month": m, "counts": by, "total": sum(by.values())})
        return rows

    lead = q(
        con,
        f"""
        SELECT worktype, count(*) AS permits, count(processed) FILTER (WHERE start_d >= processed) AS reviewed,
            quantile_cont(start_d - processed, 0.1) FILTER (WHERE start_d >= processed) AS p10,
            quantile_cont(start_d - processed, 0.25) FILTER (WHERE start_d >= processed) AS p25,
            quantile_cont(start_d - processed, 0.5) FILTER (WHERE start_d >= processed) AS median,
            quantile_cont(start_d - processed, 0.75) FILTER (WHERE start_d >= processed) AS p75,
            quantile_cont(start_d - processed, 0.9) FILTER (WHERE start_d >= processed) AS p90,
            {", ".join(f"avg((start_d - processed >= {d})::INT) FILTER (WHERE start_d >= processed) AS ge{d}" for d in LEAD_SHARES)},
            avg((start_d - processed BETWEEN 14 AND 56)::INT) FILTER (WHERE start_d >= processed) AS between14_56,
            count(*) FILTER (WHERE NOT person AND org IS NOT NULL) AS raw_org,
            count(*) FILTER (WHERE NOT person AND o.status IN ('organization', 'government')) AS named_org
        FROM cdot c LEFT JOIN org_ok o ON o.name = c.org
        WHERE c.start_d BETWEEN DATE '{LEAD_FROM}' AND DATE '{LEAD_TO}' GROUP BY worktype
    """,
    )
    by_type = []
    for r in sorted(lead, key=lambda r: CDOT_TYPES.index(r["worktype"])):
        n, rev = r["permits"], r["reviewed"]
        by_type.append(
            {
                "type": CDOT_LABEL[r["worktype"]],
                "permits": n,
                "withReviewDate": rev,
                "medianDays": rnd(r["median"], 1),
                "p10Days": rnd(r["p10"], 1),
                "p25Days": rnd(r["p25"], 1),
                "p75Days": rnd(r["p75"], 1),
                "p90Days": rnd(r["p90"], 1),
                **{f"atLeast{d}DaysShare": rnd(r[f"ge{d}"]) for d in LEAD_SHARES},
                "between14And56DaysShare": rnd(r["between14_56"]),
                "organizationShare": rnd(r["named_org"] / n if n else None),
                "rawOrganizationShare": rnd(r["raw_org"] / n if n else None),
            }
        )
    return {
        "label": "Descriptive history, not a prediction",
        "leadTimePeriod": {"from": LEAD_FROM, "to": LEAD_TO},
        "pastMonths": table(past, month_range(past_lo + timedelta(days=1), asof)),
        "nextMonths": table(nxt, month_range(asof + timedelta(days=1), hi)),
        "byType": by_type,
    }


# ----------------------------------------------------------------------------------------------------------
# Output
# ----------------------------------------------------------------------------------------------------------
CSV_FIELDS = [
    "group",
    "type",
    "event",
    "organizer",
    "start_date",
    "end_date",
    "days_until",
    "expected_from",
    "expected_to",
    "seasons_run_of_3",
    "last_date",
    "historical_recurrence_rate",
    "location",
    "community_area",
    "ward",
    "status",
    "first_seen",
    "contact_name",
    "contact_phone",
    "contact_website",
    "contact_email",
    "contact_address",
    "contact_source",
    "contact_match",
    "source",
    "id",
    "date_contacted",
    "outcome",
    "notes",
]


def location_text(e: dict) -> str:
    loc = e.get("location") or ""
    extra = e.get("segments") or 1
    if loc and extra > 1:
        loc += f" (+{extra - 1} more)"
    return loc


def csv_row(group: str, e: dict) -> dict:
    c = e.get("contact") or {}
    ca = e.get("communityArea")
    rec = e.get("recurrence")
    return {
        "group": group,
        "type": e.get("type", "Block party"),
        "event": e.get("name") or "",
        "organizer": e.get("organizer") or "",
        "start_date": e.get("startDate") or "",
        "end_date": e.get("endDate") or "",
        "days_until": e.get("daysUntil", ""),
        "expected_from": e.get("expectedStart") or "",
        "expected_to": e.get("expectedEnd") or "",
        "seasons_run_of_3": e.get("seasonsRun") or "",
        "last_date": e.get("lastDate") or "",
        "historical_recurrence_rate": rec["rate"] if rec else "",
        "location": e.get("block") or location_text(e),
        "community_area": ca["name"] if ca else "",
        "ward": e.get("ward") or "",
        "status": e.get("status") or "",
        "first_seen": e.get("firstSeen") or "",
        "contact_name": c.get("name") or "",
        "contact_phone": c.get("phone") or "",
        "contact_website": c.get("website") or "",
        "contact_email": c.get("email") or "",
        "contact_address": c.get("address") or "",
        "contact_source": c.get("source") or "",
        "contact_match": c.get("match") or "",
        "source": e.get("source") or SOURCE_CDOT,
        "id": e["id"],
        "date_contacted": "",
        "outcome": "",
        "notes": "",
    }


def json_strings(node):
    if isinstance(node, str):
        yield node
    elif isinstance(node, dict):
        for v in node.values():
            yield from json_strings(v)
    elif isinstance(node, list):
        for v in node:
            yield from json_strings(v)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", type=Path, default=JSON_OUT, help=f"JSON path for the app (default {JSON_OUT})")
    ap.add_argument("--csv", type=Path, default=None, help="CSV path (default data/events-<as-of>.csv)")
    args = ap.parse_args()

    con = db.connect()
    asof = con.execute("SELECT max(greatest(processed_date, issue_date)) FROM street_events").fetchone()[0]
    hi = asof + timedelta(days=WINDOW_DAYS)

    places, release = load_places(con)
    contacts = Contacts(con, places)
    first, sur = load_name_sets(con)
    screen = NameScreen(first, sur, set(contacts.idx.exact))
    org_status = build_org_table(con, screen)
    build_cdot(con, asof)

    up_rows = cdot_rows(con, f"c.start_d > DATE '{asof}' AND c.start_d <= DATE '{hi}'")
    cdot_up = [cdot_event(r, asof, screen) for r in up_rows]
    event_cdot = [e for e in cdot_up if e["type"] != CDOT_LABEL[BLOCK_PARTY]]
    park_raw = park_rows(con, asof, hi)
    park_up = park_events_from(park_raw, asof, screen)
    upcoming = event_cdot + park_up
    attach_contacts(upcoming, contacts)
    upcoming.sort(key=lambda e: (e["startDate"], e["type"], e["name"] or "", e["id"]))

    rates = recurrence_rates(con, asof)
    wide = cdot_rows(
        con,
        f"c.start_d > DATE '{asof}' AND c.start_d <= DATE '{asof + timedelta(days=RECURRING_DAYS)}' "
        f"AND c.worktype IN ({', '.join(repr(t) for t in lab.CDOT_LARGE)})",
    )
    wide_park = park_rows(con, asof, asof + timedelta(days=RECURRING_DAYS))
    upcoming_dates: dict[str, list[date]] = defaultdict(list)
    for r in wide:
        k = series_key_cdot(r)
        if k:
            upcoming_dates[k].append(r["start_d"])
    for r in wide_park:
        upcoming_dates[f"park|{r['event_key']}|{r['pk']}"].append(r["start_date"])
    recurring = recurring_series(con, asof, screen, upcoming_dates, rates)
    attach_contacts(recurring, contacts)
    parties = block_parties(con, asof)
    ctx = context(con, asof, upcoming, cdot_up)

    org_events = [e for e in upcoming if e["organizer"]]
    stats_up = contact_stats(upcoming)
    stats_rec = contact_stats(recurring)
    stats_all = contact_stats(upcoming + recurring)
    park_last = one(con, "SELECT max(listed_date) AS d FROM park_events")["d"]
    counts = {
        "upcoming": len(upcoming),
        "upcomingWithOrganization": len(org_events),
        "upcomingNoOrganization": len(upcoming) - len(org_events),
        "upcomingCdot": len(event_cdot),
        "upcomingPark": len(park_up),
        "upcoming2To8Weeks": sum(1 for e in org_events if 14 <= e["daysUntil"] <= 56),
        "recurring": len(recurring),
        "recurringWithOrganization": sum(1 for s in recurring if s["organizer"]),
        "recurringOnCalendar": sum(1 for s in recurring if s["onCalendar"]),
        "blockParties": parties["total"],
        "withheldOrganizerNames": sum(1 for s in org_status.values() if s == "withheld"),
        "organizerNamesScreened": len(org_status),
    }
    strip_private(upcoming)
    strip_private(recurring)

    out = {
        "generatedAt": asof.isoformat(),
        "asOf": asof.isoformat(),
        "parkListedThrough": park_last.isoformat() if park_last else None,
        "windowDays": WINDOW_DAYS,
        "recurringDays": RECURRING_DAYS,
        "definition": (
            f"Upcoming = CDOT public-way event permits (festival, parade, athletic, assembly, sidewalk sale, block "
            f"party) and Park District event reservations (event tiers 1 to 6, plus civic, corporate or philanthropic "
            f"venue rentals that name an organization) starting in the {WINDOW_DAYS} days after {asof.isoformat()}, "
            f"the newest processed or issued date in the CDOT table. Permits cancelled or denied are left out; a "
            f"permit is one row however many street segments it covers. Recurring = CDOT festival, parade, athletic "
            f"and assembly series and Park District event series that took place in at least {MIN_SEASONS} of the "
            f"last {SEASONS} twelve-month seasons ending on the as-of date, with an expected next window of the same "
            f"dates one year on, plus or minus the spread seen (at least {SPREAD_FLOOR_DAYS} days). A targeting list: "
            f"no chance of hiring anyone is modelled."
        ),
        "privacy": PRIVACY_NOTE,
        "counts": counts,
        "contactMatch": {
            "upcoming": stats_up,
            "recurring": stats_rec,
            "all": stats_all,
            "note": CONTACT_NOTE,
        },
        "upcoming": upcoming,
        "recurring": recurring,
        "recurrence": rates,
        "blockParties": parties,
        "context": ctx,
        "attribution": {"text": ATTRIBUTION, "overtureRelease": release, "contactMatch": CONTACT_NOTE},
    }
    text = json.dumps(out, separators=(",", ":"), ensure_ascii=False) + "\n"
    withheld_exact = {" ".join(tokens_of(n)) for n, st in org_status.items() if st == "withheld"}
    leak = sorted(v for v in json_strings(out) if " ".join(tokens_of(v)) in withheld_exact)
    if leak:
        raise SystemExit(f"refusing to write: {len(leak)} withheld applicant name(s) appear in the output")
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(text, encoding="utf-8")

    csv_path = args.csv or Path(f"data/events-{asof}.csv")
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=CSV_FIELDS, lineterminator="\n")
        w.writeheader()
        for e in org_events:
            w.writerow(csv_row("organizations", e))
        for s in recurring:
            w.writerow(csv_row("recurring", s))
        for e in upcoming:
            if not e["organizer"]:
                w.writerow(csv_row("no_organizer", e))
        for b in parties["items"]:
            w.writerow(csv_row("blockparties", {**b, "source": SOURCE_CDOT}))

    c = counts
    print(
        f"events as of {asof}: {c['upcoming']} upcoming in {WINDOW_DAYS} days ({c['upcomingWithOrganization']} with an "
        f"organization, {c['upcoming2To8Weeks']} of them 2-8 weeks out), {c['recurring']} recurring series "
        f"({c['recurringOnCalendar']} already on the calendar), {c['blockParties']} block parties; contact "
        f"suggestions for {stats_all['withSuggestion']} of {stats_all['organizations']} organizations "
        f"({stats_all['suggestionShare']}), with phone/website/email {stats_all['withPhoneWebsiteOrEmail']}; "
        f"wrote {args.json} and {csv_path}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
