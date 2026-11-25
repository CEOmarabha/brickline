"""Event board: every upcoming event we can see, its host and contact, and the jobs it sets off with dates.

    uv run python -m engine.leads.event_board      # after engine.leads.events and engine.leads.lifecycles

Sources: web/data/events.json (CDOT festivals, parades, races, assemblies, sidewalk sales and Park District events,
with organizer contacts), the warehouse's block_party_hosts (host name and mailing address), park_events (wedding
and private-party venue rentals; the Park District does not publish who rented), ward_offices (each alderman's
public office phone and email), and the block-party repeat rule from engine/leads/hosts.py for next season.

For every event: type label, name, dates, place, host (person, ward office or organization) with public contact
details, whether a skip trace is needed for a phone, and the lifecycle whose dated stages and services the app
shows. Partners: the Chicago businesses Overture lists in each service's primary category. Skip-trace prices,
hit rates and Do Not Call figures are cited with their source and the date read.

Host names and mailing addresses come from public records, like the owner names in snapshot.json; private
persons' phones and emails are never written here (D-027). Writes web/data/event-board.json.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import date, timedelta
from pathlib import Path

from engine import db
from engine.enrich import web
from engine.enrich.names import normalize
from engine.leads import hosts
from engine.leads.lifecycles import LIFECYCLES, VENDORS
from engine.score.signals import INVESTOR_RE
from engine.text import title

EVENTS = Path("web/data/events.json")
OUT = Path("web/data/event-board.json")
WINDOW_DAYS = 120
PARTNERS_PER_SERVICE = 5

CDOT_LIFECYCLE = "street_festival"
EVENT_LIFECYCLES = ("block_party", "street_festival", "park_wedding")
TYPE_LABEL = {
    "Festival": "Festival",
    "Parade": "Parade",
    "Athletic event": "Race or athletic event",
    "Assembly": "Rally or assembly",
    "Sidewalk sale": "Sidewalk sale or market",
    "Park District event": "Park District event",
    "Park District wedding": "Wedding",
    "Park District social rental": "Private party",
    "Park District venue rental": "Park District venue rental",
}
ORG_RE = re.compile(
    INVESTOR_RE
    + r"|\b(FOUNDATION|CHURCH|PARISH|MINISTR\w*|TEMPLE|MOSQUE|ASSOCIATION|ASSN|CHAMBER|COUNCIL|CLUB|"
    r"SCHOOL|ACADEMY|LEAGUE|CENTER|CENTRE|ORGANIZATION|COMMITTEE|NEIGHBORS|NEIGHBOURS|ALLIANCE|SOCIETY|NFP|"
    r"COALITION|COLLECTIVE|MUSEUM|LIBRARY|UNIVERSITY|COLLEGE|HOSPITAL|UNION|LODGE|VFW|POST \d+)\b"
)
WARD_RE = re.compile(r"^\s*WARD\s*(\d{1,2})\b|\bWARD\s*(\d{1,2})\s*(OFFICE|SERVICE)", re.I)

# Read 2026-11-18. Prices change; check each provider's terms allow marketing use before buying (docs/18 §5).
SKIP_TRACE = {
    "providers": [
        {"name": "Tracerfy", "price": "$0.02 per hit, pay as you go (misses free); plans from $700/month",
         "source": "https://scoutdata.com/guides/skip-tracing-services-compared"},
        {"name": "Skipmatch, DataZapp", "price": "$0.03 per match, no subscription",
         "source": "https://skipmatch.com/guides/best-skip-tracing-services-2026"},
        {"name": "REISkip", "price": "$0.15 per match, minimum 50; states a 72-82% phone hit rate",
         "source": "https://batchdata.io/blog/best-skip-tracing-services-real-estate-investors-2026-rankings"},
        {"name": "PropStream", "price": "$99/month plus $0.12 per contact (Essentials)",
         "source": "https://www.propstream.com/pricing"},
        {"name": "BatchData", "price": "$2,000/month for up to 100,000 records (volume plans; DNC and litigator flags)",
         "source": "https://batchdata.io/pricing"},
    ],
    "priceLow": 0.02,
    "priceHigh": 0.15,
    "hitRateLow": 0.72,
    "hitRateHigh": 0.82,
    "hitRateSource": "REISkip's stated phone hit rate (vendor claim; most vendors publish none)",
    # Assumption: share of personal numbers already on the Do Not Call Registry. The scrub gives the real count.
    "dncShareLow": 0.5,
    "dncShareHigh": 0.7,
    "dnc": {
        "illinoisRegistrations": 11_013_830,
        "illinoisPer100k": 86_773,
        "usRegistrations": 258_515_050,
        "asOf": "2025-09-30",
        "source": "https://www.ftc.gov/system/files/ftc_gov/pdf/DNC-Data-Book-2025.pdf",
    },
    "read": "2026-11-18",
}  # fmt: skip


def host_kind(name: str | None) -> str:
    if not name:
        return "unknown"
    if WARD_RE.search(name):
        return "ward_office"
    return "organization" if ORG_RE.search(name.upper()) else "person"


def ward_of(name: str | None) -> int | None:
    m = WARD_RE.search(name or "")
    return int(m.group(1) or m.group(2)) if m else None


# Partner picks per service: primary category, plus a business-name test where categories are loose (coworking
# offices file as event planners, FedEx as printing, cyber-security firms as security).
PARTNER_FILTERS: dict[str, tuple[str, str | None, str | None]] = {
    "event_planner": (r"party_and_event_planning|event_or_party_service|wedding_planning", None, r"REGUS|WEWORK|INDUSTRIOUS|SPACES|OFFICE|KITCHEN|PLAZA|LOFT|TOWER|^\d"),
    "party_rentals": (r"party_equipment_rental|event_or_party_service|party_supply_store|rental_service", r"RENT|TENT|PARTY|EVENT|BOUNCE|MOONWALK|TABLE|CHAIR", r"REGUS|RENT-A-CENTER|CAR|TRUCK|BIKE|WELD|HERC"),
    "linen": (r".", r"LINEN|TABLESCAPE|DRAPE", r"BLIND|CURTAIN|BED BATH"),
    "florist": (r"florist|flowers_and_gifts", r"FLOWER|FLORAL|FLORIST|BLOOM|PETAL|BLOSSOM|ROSE|STEM", None),
    "caterer": (r"^caterer$", None, None),
    "bakery": (r"bakery|cake|cupcake", None, None),
    "music": (r"dj_service", None, None),
    "photo_video": (r"event_photography|photo_booth|videographer", None, r"CLASS|SCHOOL"),
    "decor_balloons": (r".", r"BALLOON|DECOR|DRAPE|TABLESCAPE|PARTY CITY", r"HOME DECOR|FURNITURE|DESIGN PARTNERS|STAGING|FLOOR|UPHOLSTER|PAINT"),
    "av_stage": (r"audiovisual|event_technology", None, None),
    "sanitation": (r".", r"PORTABLE|POTTY|TOILET|SANITATION|PORTA[ -]?JOHN", r"BUREAU|TRAINING|DEPARTMENT"),
    "junk_dumpster": (r"junk_removal|garbage_collection|b2b_cleaning_and_waste", r"JUNK|HAUL|DUMPSTER|WASTE|DISPOSAL|REMOVAL|CLEANOUT", None),
    "cleaning_commercial": (r"janitorial|office_cleaning|cleaning_service", None, r"DUCT|MAID"),
    "cleaning_home": (r"home_cleaning|cleaning_service", None, None),
    "security": (r"security_service", r"GUARD|SECURITY|PROTECT|PATROL|K-9", r"TRUSTWAVE|CYBER"),
    "printing_signs": (r"sign_making|commercial_printer|screen_printing|printing_service", None, r"FEDEX|UPS STORE|STAPLES|OFFICE DEPOT"),
    "transport": (r"limo|party_bus|valet", None, None),
    "venue": (r"event_venue|banquet", None, None),
}  # fmt: skip


def partners(con) -> dict[str, list[dict]]:
    """Up to PARTNERS_PER_SERVICE Chicago businesses per vendor group, with a phone; one row per business name."""
    used = {
        sv.vendor for lc in LIFECYCLES if lc.id in EVENT_LIFECYCLES for st in lc.stages for sv in st.services
    }
    out = {}
    for key, (_, rx) in VENDORS.items():
        if key not in used:
            continue
        cat, keep, drop = PARTNER_FILTERS.get(key, (rx, None, None))
        rows = con.execute(
            """
            SELECT name, phones, websites, emails FROM places
            WHERE in_chicago AND status IS DISTINCT FROM 'permanently_closed' AND len(phones) > 0
              AND regexp_matches(coalesce(category, ''), ?)
              AND (? IS NULL OR regexp_matches(upper(name), ?))
              AND (? IS NULL OR NOT regexp_matches(upper(name), ?))
            ORDER BY confidence DESC NULLS LAST, name, id
        """,
            [cat, keep, keep or "", drop, drop or ""],
        ).fetchall()
        picked, seen = [], set()
        for n, ph, ws, em in rows:
            k = normalize(n)
            if k in seen:
                continue
            seen.add(k)
            picked.append(
                {
                    "name": n,
                    "phone": next((p for p in map(web.normalize_us_phone, ph or []) if p), None),
                    "website": next((w for w in map(web.clean_website, ws or []) if w), None),
                    "email": next((e.lower() for e in em or []), None),
                }
            )
            if len(picked) == PARTNERS_PER_SERVICE:
                break
        out[key] = picked
    return out


class OrgContacts:
    """Business phone, website or email for an organization host, by exact normalized name (Overture, Chicago)."""

    def __init__(self, con) -> None:
        self.by_key: dict[str, dict] = {}
        for n, ph, ws, em in con.execute("""
            SELECT name, phones, websites, emails FROM places
            WHERE in_chicago AND status IS DISTINCT FROM 'permanently_closed' ORDER BY id
        """).fetchall():
            k = normalize(n)
            if k and len(k.split()) >= 2 and k not in self.by_key:
                self.by_key[k] = {
                    "phone": next((p for p in map(web.normalize_us_phone, ph or []) if p), None),
                    "website": next((w for w in map(web.clean_website, ws or []) if w), None),
                    "email": next((e.lower() for e in em or []), None),
                    "source": "Overture Maps (name match)",
                }

    def get(self, name: str | None) -> dict | None:
        c = self.by_key.get(normalize(name or ""))
        return c if c and (c["phone"] or c["website"] or c["email"]) else None


def area_lookup(con):
    con.execute("INSTALL spatial; LOAD spatial;")
    con.execute("""
        CREATE OR REPLACE TEMP TABLE ca AS
        SELECT community_area, name, ST_GeomFromText(geom_wkt) AS geom FROM community_areas
    """)

    def find(lat: float | None, lon: float | None) -> dict | None:
        if lat is None or lon is None:
            return None
        r = con.execute(
            "SELECT community_area, name FROM ca WHERE ST_Contains(geom, ST_Point(?, ?)) ORDER BY community_area LIMIT 1",
            [lon, lat],
        ).fetchone()
        return {"id": r[0], "name": r[1]} if r else None

    return find


def host_record(name: str | None, mailing: str | None, orgs: OrgContacts, wards: dict[int, dict]) -> dict:
    kind = host_kind(name)
    rec = {"name": title(name) if name and name.isupper() else name, "type": kind, "mailing": mailing,
           "phone": None, "email": None, "website": None, "source": None, "needsSkipTrace": kind == "person"}  # fmt: skip
    if kind == "ward_office" and (w := wards.get(ward_of(name) or -1)):
        rec |= {"phone": w["phone"], "email": w["email"], "website": w["website"], "source": "City ward offices",
                "name": f"Ward {w['ward']} office ({w['alderman']})"}  # fmt: skip
    elif kind == "organization" and (c := orgs.get(name)):
        rec |= {"phone": c["phone"], "email": c["email"], "website": c["website"], "source": c["source"]}
    return rec


def build(con) -> dict:
    events_file = json.loads(EVENTS.read_text())
    as_of = date.fromisoformat(events_file["asOf"])
    end = as_of + timedelta(days=WINDOW_DAYS)
    find_area = area_lookup(con)
    orgs = OrgContacts(con)
    wards = {
        r[0]: {"ward": r[0], "alderman": r[1], "address": r[2], "phone": r[3], "email": r[4], "website": r[5]}
        for r in con.execute(
            "SELECT ward, alderman, address, phone, email, website FROM ward_offices WHERE ward IS NOT NULL ORDER BY ward"
        ).fetchall()
    }
    events: list[dict] = []
    for e in events_file["upcoming"]:
        contact = e.get("contact") or {}
        org = e.get("organizer")
        events.append(
            {
                "id": e["id"],
                "category": TYPE_LABEL.get(e["type"], e["type"]),
                "lifecycle": CDOT_LIFECYCLE,
                "name": e.get("name") or TYPE_LABEL.get(e["type"], e["type"]),
                "start": e["startDate"],
                "end": e.get("endDate"),
                "place": e.get("location"),
                "area": e.get("communityArea"),
                "ward": e.get("ward"),
                "status": e.get("status"),
                "source": e.get("source"),
                "host": {
                    "name": org,
                    "type": "organization" if org else "unknown",
                    "mailing": contact.get("address"),
                    "phone": contact.get("phone"),
                    "email": contact.get("email"),
                    "website": contact.get("website"),
                    "source": contact.get("source"),
                    "needsSkipTrace": False,
                },
            }
        )
    for r in con.execute(f"""
        SELECT permit_no, start_date, end_date, event_name, host_name,
            nullif(concat_ws(', ', host_street, trim(concat_ws(' ', host_city, host_state, host_zip))), '') AS mailing,
            block, ward, lat, lon, status
        FROM block_party_hosts
        WHERE start_date > DATE '{as_of}' AND start_date <= DATE '{end}' AND status IS DISTINCT FROM 'Cancelled'
        ORDER BY start_date, permit_no
    """).fetchall():
        permit, start, finish, name, host, mailing, block, ward, lat, lon, status = r
        events.append(
            {
                "id": f"bp-{permit}",
                "category": "Block party",
                "lifecycle": "block_party",
                "name": name or "Block party",
                "start": start.isoformat(),
                "end": finish.isoformat() if finish else None,
                "place": title(block) if block else None,
                "area": find_area(lat, lon),
                "ward": ward,
                "status": status,
                "source": "Chicago Department of Transportation permits",
                "host": host_record(host, title(mailing) if mailing else None, orgs, wards),
            }
        )
    already = {(e["start"], e.get("place"), e["category"]) for e in events}
    for r in con.execute(f"""
        SELECT event_type, park_name, start_date, end_date, status, count(*) AS n
        FROM park_events
        WHERE event_type IN ('Venue Rental - Wedding', 'Venue Rental - Social')
          AND start_date > DATE '{as_of}' AND start_date <= DATE '{end}'
          AND coalesce(status, '') NOT IN ('Stage Denied', 'Cancelled', 'Denied')
        GROUP BY ALL ORDER BY start_date, park_name, event_type
    """).fetchall():
        kind, park, start, finish, status, _ = r
        category = "Wedding" if kind.endswith("Wedding") else "Private party"
        if (start.isoformat(), park, category) in already:
            continue
        events.append(
            {
                "id": f"park-{start}-{normalize(park).replace(' ', '-').lower()}-{kind[-6:].lower()}",
                "category": category,
                "lifecycle": "park_wedding",
                "name": f"{'Wedding' if kind.endswith('Wedding') else 'Private party'} at {park}",
                "start": start.isoformat(),
                "end": finish.isoformat() if finish else None,
                "place": park,
                "area": None,
                "ward": None,
                "status": status,
                "source": "Chicago Park District reservations",
                "host": {
                    "name": None,
                    "type": "unknown",
                    "mailing": None,
                    "phone": None,
                    "email": None,
                    "website": None,
                    "source": "The Park District does not publish who rented; ask the venue",
                    "needsSkipTrace": False,
                },  # fmt: skip
            }
        )
    events.sort(key=lambda x: (x["start"], x["category"], x["id"]))

    target, past = hosts.seasons(as_of)
    backtest = hosts.backtest(con, target - 1)
    _, likely = hosts.block_lists(con, as_of)
    predicted = []
    for r in likely:
        last = r["last_party"]
        try:
            guess = last.replace(year=target)
        except ValueError:
            guess = last.replace(year=target, day=28)
        predicted.append(
            {
                "id": f"likely-{target}-{normalize(r['block'] or '').replace(' ', '-').lower()}",
                "category": "Block party (likely next season)",
                "lifecycle": "block_party",
                "name": f"Block party, {title(r['block']) if r['block'] else 'block not given'}",
                "start": guess.isoformat(),
                "end": None,
                "place": title(r["block"]) if r["block"] else None,
                "area": None,
                "ward": r["ward"],
                "status": f"Held in {r['past_seasons']} of {past[0]}-{past[-1]}; last on {last.isoformat()}",
                "chance": backtest.get(int(r["past_seasons"]), {}).get("repeatRate"),
                "source": "Chicago Department of Transportation permits (repeat rule, engine/leads/hosts.py)",
                "host": host_record(
                    r["host_name"],
                    title(
                        ", ".join(
                            x for x in (r["host_street"], r["host_city"], r["host_state"], r["host_zip"]) if x
                        )
                    )
                    or None,
                    orgs,
                    wards,
                ),
            }
        )
    seen: set[str] = set()
    for p in predicted:
        base, n = p["id"], 2
        while p["id"] in seen:
            p["id"] = f"{base}-{n}"
            n += 1
        seen.add(p["id"])

    def people(rows: list[dict]) -> int:
        return sum(1 for x in rows if x["host"]["needsSkipTrace"])

    return {
        "asOf": as_of.isoformat(),
        "windowDays": WINDOW_DAYS,
        "season": target,
        "backtest": {str(k): v for k, v in backtest.items()},
        "events": events,
        "predicted": predicted,
        "wards": {str(k): v for k, v in wards.items()},
        "partners": partners(con),
        "skipTrace": SKIP_TRACE
        | {
            "upcomingPeople": people(events),
            "predictedPeople": people(predicted),
            "predictedHosts": len(predicted),
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    data = build(db.connect())
    args.out.write_text(json.dumps(data, separators=(",", ":"), ensure_ascii=False, default=str) + "\n")
    cats: dict[str, int] = {}
    for e in data["events"]:
        cats[e["category"]] = cats.get(e["category"], 0) + 1
    kinds: dict[str, int] = {}
    for e in data["events"] + data["predicted"]:
        kinds[e["host"]["type"]] = kinds.get(e["host"]["type"], 0) + 1
    print(
        f"wrote {args.out} ({args.out.stat().st_size / 1e3:.0f} KB): {len(data['events'])} upcoming events {cats}; "
        f"{len(data['predicted'])} likely block parties in {data['season']}; hosts by type {kinds}; "
        f"skip trace needed: {data['skipTrace']['upcomingPeople']} upcoming, {data['skipTrace']['predictedPeople']} predicted"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
