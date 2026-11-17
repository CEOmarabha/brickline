"""Who to sell each pilot list to: public business listings and permit-named contractors, per list.

    uv run python -m engine.leads.buyers

Pilot lists (see docs/14-sales-playbook.md section 5d, docs/HANDOFF.md next task 2): new business coming, trades
still open after big permits, closed restaurant spaces, and the pest-control pilot. For each list this builds a
deduplicated, ranked, capped list of Chicago-area companies likely to buy it, with business contact details and an
evidence line that says why the company is on the list.

Sources, always labelled on every row:
  * "Overture Maps": places in Chicago (`places.in_chicago`) whose primary category is one of the segment's
    categories. Contact fields (phone, website, email) are Overture's; websites are http(s) only and exclude social
    media, directories and government pages. Nothing is guessed.
  * "Chicago building permits": contractors named on permits in the last 12 months (trade role or permit text),
    ranked by the number of permits. They are matched to an Overture place only when the normalized name is
    identical (or the permit's 30-character-cut name is a prefix of it), the place's category fits the trade and
    one business remains after the same-website/same-phone check; the match supplies phone, website and email.
    Unmatched contractors stay on the list without contact details.
  * "Chicago business licenses": only used by the pest list (same logic as engine.leads.pest).

Writes web/data/buyers.json (the app's /pilots hub and /export/buyers) and data/buyers-<as-of>.csv. Read-only on
the warehouse. Deterministic: every sort has explicit tie-breaks and floats are rounded before writing.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import duckdb

from engine import db
from engine.enrich import web
from engine.enrich.contacts import PlaceIndex, plain_email_ok
from engine.enrich.names import normalize
from engine.leads import pest
from engine.score.signals import q
from engine.text import title

JSON_OUT = Path("web/data/buyers.json")

PERMIT_DAYS = 365
MIN_PERMITS = 3
MIN_PERMITS_RESTAURANT_GC = 2
TRUNCATED_LEN = 29  # permit party names are cut at 30 characters
SOURCE_PERMITS = "Chicago building permits"
SOURCE_OVERTURE = "Overture Maps"
SOURCE_LICENSES = "Chicago business licenses"
SOURCE_ORDER = (SOURCE_PERMITS, SOURCE_OVERTURE, SOURCE_LICENSES)
ATTRIBUTION = (
    "Business listings (c) Overture Maps Foundation, CDLA-Permissive-2.0; sources include Meta and Microsoft. "
    "Contractor names: City of Chicago building permits open data (not an endorsement by the City)."
)
CONTACT_NOTE = (
    "Phone, website and email come from Overture Maps listings; a permit-named contractor gets them only when an "
    "Overture place has the identical normalized name (never guessed). Verify before use and call business lines "
    "by hand only."
)

GENERIC_CONTRACTOR_CATEGORIES = (
    "contractor",
    "building_or_construction_service",
    "building_contractor",
    "altering_and_remodeling_contractor",
    "electrician",
)
GOV_HOST = re.compile(r"(?:^|\.)(?:gov|mil)$|(?:^|\.)cityofchicago\.org$")
STARTS_WITH_NUMBER = r"^\s*\d"


@dataclass(frozen=True)
class PermitRule:
    """Contractors named on permits in the last 12 months. `cond` is SQL over p (permits) and pp (permit_parties)."""

    cond: str
    phrase: str  # "named as elevator contractor on {n} {permits}"
    noun: str  # singular noun for permits ("permit", "sign permit")
    min_jobs: int = MIN_PERMITS
    role_label: str = "Contractor"


@dataclass(frozen=True)
class Segment:
    key: str
    label: str
    cap: int
    categories: tuple[str, ...] = ()
    strong_categories: tuple[str, ...] = ()  # ranked ahead of the other categories
    hint: str | None = None  # name regex that ranks a company ahead ("commercial", "business")
    hint_text: str = ""
    exclude_name: str | None = None
    permit: PermitRule | None = None
    compat: tuple[str, ...] = ()  # extra Overture categories a permit-named contractor may match
    pest: bool = False


@dataclass(frozen=True)
class ListSpec:
    key: str
    title: str
    segments: tuple[Segment, ...]


CLEANING = Segment(
    "cleaning",
    "Commercial cleaning and janitorial",
    15,
    categories=("janitorial_service", "office_cleaning", "cleaning_service"),
    strong_categories=("janitorial_service", "office_cleaning"),
    exclude_name=r"\bmaids?\b|house ?(?:keep|clean)|home clean|residential|laundry|dry clean",
)
SIGNS_OVERTURE = ("sign_making", "b2b_signage_service")

LISTS: tuple[ListSpec, ...] = (
    ListSpec(
        "newBusiness",
        "New business coming",
        (
            CLEANING,
            Segment("signage", "Sign shops", 15, categories=SIGNS_OVERTURE),
            Segment(
                "security",
                "Security and alarm companies",
                15,
                categories=("security_systems", "security_service"),
                strong_categories=("security_systems",),
                exclude_name=r"training|academy|school|investigat",
            ),
            Segment(
                "insurance",
                "Insurance agents",
                15,
                categories=("insurance_agency",),
                hint=r"commercial|business|\brisk\b|broker",
                hint_text="name suggests commercial or business lines",
            ),
            Segment(
                "movers",
                "Commercial movers",
                15,
                categories=("mover",),
                hint=r"commercial|office|business|corporate|relocation",
                hint_text="name suggests office or commercial moves",
            ),
        ),
    ),
    ListSpec(
        "openTrades",
        "Trades still open after big permits",
        (
            Segment(
                "elevator",
                "Elevator contractors",
                15,
                categories=("elevator_service",),
                permit=PermitRule(
                    "pp.role = 'elevator'",
                    "named as elevator contractor on {n} {permits}",
                    "permit",
                    role_label="Elevator contractor",
                ),
                compat=("elevator_service",),
            ),
            Segment(
                "electrical",
                "Electrical contractors",
                15,
                categories=("electrician",),
                permit=PermitRule(
                    "pp.role = 'electrical' AND p.permit_type IN "
                    "('PERMIT - RENOVATION/ALTERATION', 'PERMIT - NEW CONSTRUCTION')",
                    "named as electrical contractor on {n} renovation or new-construction {permits}",
                    "permit",
                    role_label="Electrical contractor",
                ),
                compat=("electrician",),
            ),
            Segment(
                "fireAlarm",
                "Fire-alarm and fire-protection contractors",
                15,
                categories=("fire_protection_service",),
                exclude_name=(
                    r"\bengine\b|\btruck\b|\bladder\b|firehouse|fire (?:station|department|dept|prevention|academy)"
                    r"|battalion|\bCFD\b|fire ?fighter"
                ),
                permit=PermitRule(
                    "pp.role_raw = 'PRIVATE ALARM CONTRACTOR'",
                    "named as private alarm contractor on {n} {permits}",
                    "permit",
                    role_label="Alarm contractor",
                ),
                compat=("fire_protection_service", "security_systems"),
            ),
            Segment(
                "signs",
                "Sign contractors",
                15,
                categories=SIGNS_OVERTURE,
                permit=PermitRule(
                    "(pp.role = 'sign' OR (p.permit_type = 'PERMIT - SIGNS' AND pp.role = 'gc'))",
                    "named as sign or general contractor on {n} sign {permits}",
                    "sign permit",
                    role_label="Sign contractor",
                ),
                compat=SIGNS_OVERTURE,
            ),
        ),
    ),
    ListSpec(
        "closedRestaurant",
        "Closed restaurant spaces",
        (
            Segment(
                "gc",
                "Restaurant build-out general contractors",
                20,
                permit=PermitRule(
                    "pp.role = 'gc' AND p.permit_type IN ('PERMIT - RENOVATION/ALTERATION', "
                    "'PERMIT - NEW CONSTRUCTION', 'PERMIT - EXPRESS PERMIT PROGRAM') AND regexp_matches("
                    "p.description, 'RESTAURANT|\\bCAFE\\b|COFFEE|BAKERY|TAVERN|\\bPUB\\b|BAR AND GRILL|TAKE-?OUT"
                    "|FOOD (SERVICE|ESTABLISHMENT|PREP)|COMMERCIAL KITCHEN')",
                    "general contractor on {n} {permits} whose text mentions a restaurant, cafe, bakery or similar",
                    "permit",
                    min_jobs=MIN_PERMITS_RESTAURANT_GC,
                    role_label="General contractor",
                ),
            ),
            Segment(
                "kitchen",
                "Kitchen equipment dealers",
                15,
                categories=("restaurant_equipment_and_supply",),
            ),
            Segment(
                "brokers",
                "Commercial real estate brokers",
                15,
                categories=("commercial_real_estate",),
                exclude_name=STARTS_WITH_NUMBER,
            ),
            Segment("signage", "Sign shops", 15, categories=SIGNS_OVERTURE),
        ),
    ),
    ListSpec("pest", "Pest-control pilot", (Segment("pest", "Pest-control companies", 60, pest=True),)),
)


@dataclass
class Entry:
    segment: str
    name: str
    category: str | None = None
    address: str | None = None
    phone: str | None = None
    website: str | None = None
    email: str | None = None
    sources: set[str] = field(default_factory=set)
    permits: int = 0
    last_permit: date | None = None
    permit_evidence: str | None = None
    overture_category: str | None = None
    hint: bool = False
    strong: bool = False
    confidence: float = 0.0
    place_id: str = ""
    name_key: str = ""
    licensed_as: str | None = None

    def contact_score(self) -> int:
        return int(bool(self.phone)) + int(bool(self.website)) + int(bool(self.email))

    def has_reach(self) -> bool:
        return bool(self.phone or self.website)


def cat_label(category: str | None) -> str | None:
    return (category or "").replace("_", " ") or None


def plural(n: int, noun: str) -> str:
    return noun if n == 1 else f"{noun}s"


def pretty(name: str) -> str:
    return title(name) if name.isupper() else name.strip()


def usable_site(values) -> str | None:
    site = pest.website_of(values)
    if site and GOV_HOST.search(web.base_host(web.host_of(site))):
        return None
    return site


def load_places(con: duckdb.DuckDBPyConnection, categories: set[str]) -> list[dict]:
    cur = con.execute(
        f"""
        SELECT id, name, category, phones, websites, emails, address, locality, postcode, confidence, in_chicago,
          release
        FROM places
        WHERE status IS DISTINCT FROM 'permanently_closed' AND category IN ({", ".join("?" * len(categories))})
          AND name IS NOT NULL
        ORDER BY id
        """,
        sorted(categories),
    )
    cols = [c[0] for c in cur.description]
    rows = [dict(zip(cols, r, strict=True)) for r in cur.fetchall()]
    for r in rows:
        r["phone"] = pest.phone_of(r["phones"])
        r["site"] = usable_site(r["websites"])
        mail = pest.email_of(r["emails"])
        r["mail"] = mail if mail and plain_email_ok(mail) else None
        r["key"] = normalize(r["name"])
    return rows


def place_entry(seg: Segment, p: dict) -> Entry:
    name = pretty(p["name"])
    return Entry(
        segment=seg.key,
        name=name,
        category=cat_label(p["category"]),
        address=", ".join(x for x in (p["address"], p["locality"], p["postcode"]) if x) or None,
        phone=p["phone"],
        website=p["site"],
        email=p["mail"],
        sources={SOURCE_OVERTURE},
        overture_category=cat_label(p["category"]),
        hint=bool(seg.hint and re.search(seg.hint, p["name"], re.I)),
        strong=p["category"] in seg.strong_categories,
        confidence=float(p["confidence"] or 0.0),
        place_id=p["id"],
        name_key=p["key"],
    )


def segment_places(seg: Segment, places: list[dict]) -> list[dict]:
    """Chicago places in the segment's categories, minus excluded names, with a way to reach them."""
    out = []
    for p in places:
        if p["category"] not in seg.categories or not p["in_chicago"] or not p["key"]:
            continue
        if seg.exclude_name and re.search(seg.exclude_name, p["name"], re.I):
            continue
        if not (p["phone"] or p["site"]):
            continue
        out.append(p)
    return out


def identity(p: dict) -> str:
    return p["phone"] or p["site"] or p["id"]


def match_permit_name(raw_name: str, idx: PlaceIndex) -> dict | None:
    """The one Overture place a permit contractor name stands for, or None when unsure.

    Same rules as engine.enrich.contacts: identical normalized name (anywhere in the metro), a typo-level match
    (Chicago places only), or the 30-character-cut permit name as a prefix; the place's category must fit the trade
    (the index only holds fitting categories) and all candidates must be one business (same phone or website).
    """
    key = normalize(raw_name)
    if not key:
        return None
    hits = idx.exact.get(key, [])
    method = "exact"
    if not hits and len(key.split()) >= 2:
        hits, method = idx.fuzzy(key), "fuzzy"
    if not hits and len(raw_name) >= TRUNCATED_LEN:
        hits, method = idx.truncated(key), "truncated"
    pool = [idx.rows[i] for i in hits]
    if method == "fuzzy":
        pool = [p for p in pool if p["in_chicago"]]
    in_city = [p for p in pool if p["in_chicago"]]
    pool = in_city or pool
    if not pool or len({identity(p) for p in pool}) > 1:
        return None
    return sorted(pool, key=lambda p: (not p["site"], not p["phone"], -(p["confidence"] or 0), p["id"]))[0]


def permit_entries(
    con: duckdb.DuckDBPyConnection, asof: date, seg: Segment, places: list[dict]
) -> list[Entry]:
    rule = seg.permit
    assert rule is not None
    rows = q(
        con,
        f"""
        SELECT pp.name_key, count(DISTINCT p.id) AS n, max(p.issue_date) AS last_d,
          first(pp.name_raw ORDER BY p.issue_date DESC, p.id, pp.name_raw) AS name_raw
        FROM permits p JOIN permit_parties pp ON pp.permit_id = p.id
        WHERE p.issue_date > DATE '{asof}' - INTERVAL {PERMIT_DAYS} DAY AND pp.name_key <> '' AND ({rule.cond})
        GROUP BY pp.name_key
        HAVING n >= {rule.min_jobs}
        ORDER BY n DESC, pp.name_key
        """,
    )
    generic = set(GENERIC_CONTRACTOR_CATEGORIES) | set(seg.compat)
    idx = PlaceIndex([dict(p) for p in places if p["category"] in generic])
    out = []
    for r in rows:
        e = Entry(
            segment=seg.key,
            name=pretty(r["name_raw"]),
            category=rule.role_label,
            sources={SOURCE_PERMITS},
            permits=r["n"],
            last_permit=r["last_d"],
            name_key=normalize(r["name_raw"]),
        )
        e.permit_evidence = (
            rule.phrase.format(n=r["n"], permits=plural(r["n"], rule.noun))
            + f" in the last 12 months (latest {r['last_d'].isoformat()})"
        )
        p = match_permit_name(r["name_raw"], idx)
        if p is not None:
            e.sources.add(SOURCE_OVERTURE)
            e.name = pretty(p["name"]) if len(r["name_raw"]) >= TRUNCATED_LEN else e.name
            e.category = rule.role_label
            e.overture_category = cat_label(p["category"])
            e.address = ", ".join(x for x in (p["address"], p["locality"], p["postcode"]) if x) or None
            e.phone, e.website, e.email = p["phone"], p["site"], p["mail"]
            e.confidence = float(p["confidence"] or 0.0)
            e.place_id = p["id"]
        out.append(e)
    return out


def pest_entries(con: duckdb.DuckDBPyConnection, seg: Segment) -> list[Entry]:
    _, pests, _ = pest.load_places(con)
    out = []
    for c in pest.pest_companies(con, pests):
        if not c["name"]:
            continue
        sources = {SOURCE_OVERTURE}
        if c["licensedLegalName"]:
            sources.add(SOURCE_LICENSES)
        out.append(
            Entry(
                segment=seg.key,
                name=c["name"],
                category=c["category"],
                address=c["address"],
                phone=c["phone"],
                website=c["website"],
                email=c["email"],
                sources=sources,
                overture_category=c["category"],
                name_key=normalize(c["name"]),
                licensed_as=c["licensedLegalName"],
            )
        )
    return out


def merge(a: Entry, b: Entry) -> Entry:
    """Combine two records of one business: keep the one with more permits, then more contact details."""
    first, second = sorted(
        (a, b), key=lambda e: (-e.permits, -e.contact_score(), -e.confidence, e.name.lower(), e.place_id)
    )
    first.sources |= second.sources
    for attr in ("phone", "website", "email", "address", "overture_category", "licensed_as"):
        if not getattr(first, attr):
            setattr(first, attr, getattr(second, attr))
    first.permits = max(first.permits, second.permits)
    first.last_permit = first.last_permit or second.last_permit
    first.permit_evidence = first.permit_evidence or second.permit_evidence
    first.confidence = max(first.confidence, second.confidence)
    first.place_id = first.place_id or second.place_id
    return first


def dedupe(entries: list[Entry]) -> list[Entry]:
    """One entry per business: the same phone, the same website, or the same name at one website host.

    A permit-named contractor also absorbs a listing with the identical normalized name.
    """
    entries = sorted(
        entries, key=lambda e: (-e.permits, -e.contact_score(), -e.confidence, e.name.lower(), e.place_id)
    )
    groups: list[list[Entry]] = []
    index: dict[tuple[str, str], int] = {}
    for e in entries:
        host = web.base_host(web.host_of(e.website)) if e.website else ""
        keys = []
        if e.phone:
            keys.append(("phone", e.phone))
        if e.website:
            keys.append(("site", e.website))
        if host and e.name_key:
            keys.append(("name_host", f"{e.name_key}|{host}"))
        if e.name_key:
            keys.append(("name_permit", e.name_key))
        gi = next(
            (index[k] for k in keys if k in index and (k[0] != "name_permit" or groups[index[k]][0].permits)),
            None,
        )
        if gi is None:
            gi = len(groups)
            groups.append([])
        groups[gi].append(e)
        for k in keys:
            if k[0] != "name_permit" or e.permits:
                index.setdefault(k, gi)
    out = []
    for g in groups:
        cur = g[0]
        for e in g[1:]:
            cur = merge(cur, e)
        out.append(cur)
    return out


def rank_key(e: Entry):
    return (
        -e.permits,
        not e.strong,
        not e.hint,
        -e.contact_score(),
        -e.confidence,
        e.name.lower(),
        e.name,
        e.place_id,
    )


def evidence_line(seg: Segment, e: Entry) -> str:
    parts = []
    if e.permit_evidence:
        parts.append(e.permit_evidence)
    if e.overture_category:
        cat = f"Overture category: {e.overture_category}"
        if not e.permit_evidence:
            cat += " (listed in Chicago)"
        parts.append(cat)
    if e.hint and seg.hint_text:
        parts.append(seg.hint_text)
    if e.licensed_as:
        parts.append(f"licensed as {e.licensed_as} (Chicago business licenses)")
    return "; ".join(parts)


def segment_entries(
    con: duckdb.DuckDBPyConnection, asof: date, seg: Segment, places: list[dict]
) -> tuple[list[Entry], int]:
    """Ranked, capped entries of one segment and how many distinct businesses were available."""
    entries: list[Entry] = []
    if seg.pest:
        entries += pest_entries(con, seg)
    else:
        entries += [place_entry(seg, p) for p in segment_places(seg, places)]
        if seg.permit:
            entries += permit_entries(con, asof, seg, places)
    entries = dedupe(entries)
    entries.sort(key=rank_key)
    return entries[: seg.cap], len(entries)


def rnd(x: float | None, digits: int = 4) -> float | None:
    return None if x is None else round(float(x), digits)


def share(n: int, total: int) -> float | None:
    return rnd(n / total) if total else None


def coverage(rows: list[Entry]) -> dict:
    n = len(rows)
    return {
        "buyers": n,
        "withPhone": sum(1 for e in rows if e.phone),
        "withWebsite": sum(1 for e in rows if e.website),
        "withEmail": sum(1 for e in rows if e.email),
        "withAnyContact": sum(1 for e in rows if e.has_reach()),
        "phoneShare": share(sum(1 for e in rows if e.phone), n),
        "websiteShare": share(sum(1 for e in rows if e.website), n),
        "emailShare": share(sum(1 for e in rows if e.email), n),
        "anyContactShare": share(sum(1 for e in rows if e.has_reach()), n),
    }


CSV_FIELDS = [
    "list",
    "buyer_type",
    "company",
    "category",
    "address",
    "phone",
    "website",
    "email",
    "sources",
    "evidence",
    "permits_last_12_months",
    "latest_permit_date",
    "date_contacted",
    "outcome",
    "notes",
]


def entry_json(seg: Segment, e: Entry) -> dict:
    return {
        "segment": seg.key,
        "name": e.name,
        "category": e.category,
        "address": e.address,
        "phone": e.phone,
        "website": e.website,
        "email": e.email,
        "sources": sorted(e.sources, key=SOURCE_ORDER.index),
        "evidence": evidence_line(seg, e),
        "permits": e.permits or None,
        "lastPermit": e.last_permit.isoformat() if e.last_permit else None,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", type=Path, default=JSON_OUT, help=f"JSON path for the app (default {JSON_OUT})")
    ap.add_argument("--csv", type=Path, default=None, help="CSV path (default data/buyers-<as-of>.csv)")
    args = ap.parse_args()

    con = db.connect()
    asof = con.execute("SELECT max(issue_date) FROM permits").fetchone()[0]
    segments = [s for spec in LISTS for s in spec.segments]
    categories = {c for s in segments for c in (*s.categories, *s.compat)} | set(
        GENERIC_CONTRACTOR_CATEGORIES
    )
    places = load_places(con, categories)
    release = places[0]["release"] if places else ""

    lists_out = []
    csv_rows = []
    for spec in LISTS:
        all_rows: list[Entry] = []
        seg_out = []
        buyers = []
        for seg in spec.segments:
            rows, available = segment_entries(con, asof, seg, places)
            all_rows += rows
            seg_out.append(
                {
                    "key": seg.key,
                    "label": seg.label,
                    "listed": len(rows),
                    "available": available,
                    "cap": seg.cap,
                    "permitDerived": seg.permit is not None,
                    **coverage(rows),
                }
            )
            for e in rows:
                j = entry_json(seg, e)
                buyers.append(j)
                csv_rows.append(
                    {
                        "list": spec.key,
                        "buyer_type": seg.label,
                        "company": e.name,
                        "category": e.category or "",
                        "address": e.address or "",
                        "phone": e.phone or "",
                        "website": e.website or "",
                        "email": e.email or "",
                        "sources": "; ".join(j["sources"]),
                        "evidence": j["evidence"],
                        "permits_last_12_months": e.permits or "",
                        "latest_permit_date": j["lastPermit"] or "",
                        "date_contacted": "",
                        "outcome": "",
                        "notes": "",
                    }
                )
        lists_out.append(
            {
                "key": spec.key,
                "title": spec.title,
                "segments": seg_out,
                "counts": coverage(all_rows),
                "buyers": buyers,
            }
        )

    out = {
        "generatedAt": asof.isoformat(),
        "asOf": asof.isoformat(),
        "definition": (
            "Chicago-area companies that could buy a pilot list, from Overture Maps business listings (Chicago, "
            "primary category match) and from contractors named on Chicago building permits in the last "
            f"{PERMIT_DAYS} days (at least {MIN_PERMITS} permits, {MIN_PERMITS_RESTAURANT_GC} for restaurant "
            "general contractors). Each buyer type is capped and ranked by permit count, then category fit, then "
            "contact details and listing confidence, then name. A list is a place to start calling or emailing "
            "by hand, not a promise that anyone will buy."
        ),
        "windows": {
            "permitDays": PERMIT_DAYS,
            "minPermits": MIN_PERMITS,
            "minPermitsRestaurantGc": MIN_PERMITS_RESTAURANT_GC,
        },
        "lists": lists_out,
        "attribution": {"text": ATTRIBUTION, "overtureRelease": release, "contactMatch": CONTACT_NOTE},
    }
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(out, separators=(",", ":"), ensure_ascii=False) + "\n", encoding="utf-8")

    csv_path = args.csv or Path(f"data/buyers-{asof}.csv")
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=CSV_FIELDS, lineterminator="\n")
        w.writeheader()
        w.writerows(csv_rows)

    for lst in lists_out:
        c = lst["counts"]
        print(
            f"{lst['key']}: {c['buyers']} buyers "
            f"(phone {c['phoneShare']:.0%}, website {c['websiteShare']:.0%}, email {c['emailShare']:.0%}, "
            f"any contact {c['anyContactShare']:.0%})"
        )
        for s in lst["segments"]:
            print(f"    {s['key']}: {s['listed']} of {s['available']} available")
    print(f"buyers as of {asof}: wrote {args.json} and {csv_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
