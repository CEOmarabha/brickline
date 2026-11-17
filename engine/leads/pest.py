"""H23 pest-control PILOT list: restaurants with a fresh pest finding, plus pest-control companies to pitch.

    uv run python -m engine.leads.pest

Pilot only (docs/13-signal-lab.md H23, docs/HANDOFF.md next task 5): the founder offers a weekly list to one
pest-control company and records their win rate. Nothing here models a probability, chance of work or expected
value; every number is descriptive history computed from the warehouse at run time.

Writes web/data/pest.json (the app's /pilots/pest page and /export/pest) and data/pest-<as-of>.csv (the weekly
rows, for printing or emailing to the pilot client). Read-only on the warehouse. Deterministic: ties are broken
explicitly and floats are rounded before writing.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

import duckdb

from engine import db
from engine.enrich import web
from engine.enrich.names import normalize, token_set_ratio
from engine.score.food import VALID_RESULT
from engine.score.signals import q
from engine.text import title
from engine.warehouse import address_key_sql, food_text_sql

JSON_OUT = Path("web/data/pest.json")

EPISODE_GAP_DAYS = (
    180  # a finding is "fresh" when none at the license in the prior 180 days (the lab's H23 episode)
)
WEEK_DAYS = 7
BACKFILL_DAYS = 28
HISTORY_DAYS = 730
OPERATOR_DAYS = 365
CONTEXT_WEEKS = 52
TOP_AREAS = 10
NAME_MATCH_MIN = 0.88  # token-set ratio between the inspection DBA and an Overture place name, same address
LATER_RESULT = "results IN ('Pass', 'Pass w/ Conditions', 'Fail', 'Out of Business')"
SOURCE = "Overture Maps"
ATTRIBUTION = (
    "Places data (c) Overture Maps Foundation, CDLA-Permissive-2.0; sources include Meta and Microsoft. "
    "Inspections: City of Chicago Food Inspections open data (not an endorsement by the City)."
)

# Violation text is upper-case "<n>. <HEADING> - Comments: <inspector text>" items joined by " | ". The
# "INSECTS, RODENTS, & ANIMALS NOT PRESENT" heading would match every term, so it is removed before the term search.
PEST_HEADING = r"INSECTS, RODENTS,? (?:AND|&) ANIMALS NOT PRESENT"
PEST_TERMS: tuple[tuple[str, str], ...] = (
    ("rodents", r"RODENT"),
    ("mice", r"\bMICE\b|\bMOUSE\b"),
    ("rats", r"\bRATS?\b"),
    ("droppings", r"DROPPINGS"),
    ("roaches", r"ROACH"),
    ("flies", r"\bFLIES\b|\bFLY\b"),
    ("insects", r"INSECT|\bBUGS?\b|\bANTS\b"),
    ("pests", r"\bPESTS?\b|VERMIN"),
)
GENERAL_TERM = "pest item cited"
PEST_COMPANY_RX = r"pest|exterminat|rodent|termite|vermin"
PEST_LICENSE_RX = r"PEST|EXTERMINAT|RODENT"

SOCIAL_NOTE = "Overture places carry no social profiles in this subset; none are shown."


def esc(pattern: str) -> str:
    return pattern.replace("'", "''")


def rnd(x: float | None, digits: int = 4) -> float | None:
    return None if x is None else round(float(x), digits)


def first_value(values, clean) -> str | None:
    for v in values or []:
        c = clean(v)
        if c:
            return c
    return None


def phone_of(values) -> str | None:
    return first_value(values, lambda v: web.normalize_us_phone(v) if v else None)


def website_of(values) -> str | None:
    return first_value(values, web.clean_website)


def email_of(values) -> str | None:
    return first_value(values, lambda v: v.strip().lower() if v and "@" in v else None)


# ----------------------------------------------------------------------------------------------------------
# Episodes
# ----------------------------------------------------------------------------------------------------------
def build_tables(con: duckdb.DuckDBPyConnection, asof: date) -> None:
    con.execute("INSTALL spatial; LOAD spatial;")
    con.execute("""
        CREATE OR REPLACE TEMP TABLE ca_geom AS
        SELECT community_area, name, ST_GeomFromText(geom_wkt) AS geom FROM community_areas
    """)
    con.execute("""
        CREATE OR REPLACE TEMP TABLE addr_pt AS
        SELECT address_key, median(lat) AS lat, median(lon) AS lon FROM food_inspections
        WHERE lat IS NOT NULL AND lon IS NOT NULL AND address_key IS NOT NULL GROUP BY 1
    """)
    text = food_text_sql("violations")
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE rest AS
        SELECT inspection_id, license_no, dba, address_key, inspection_date AS d, inspection_type, results, risk,
          f_pest, lat, lon, {text} AS vtext
        FROM food_inspections
        WHERE facility_type = 'Restaurant' AND license_no > 0 AND {LATER_RESULT}
    """)
    # One pest-finding inspection per (license, date): the lowest inspection_id.
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE pest_day AS
        SELECT * FROM rest WHERE f_pest AND {VALID_RESULT}
        QUALIFY row_number() OVER (PARTITION BY license_no, d ORDER BY inspection_id) = 1
    """)
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE episode AS
        SELECT * FROM (
          SELECT *, lag(d) OVER (PARTITION BY license_no ORDER BY d) AS prev_d FROM pest_day
        ) WHERE prev_d IS NULL OR d - prev_d > {EPISODE_GAP_DAYS}
    """)
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE episode_area AS
        WITH pt AS (
          SELECT e.inspection_id, coalesce(e.lat, a.lat) AS lat, coalesce(e.lon, a.lon) AS lon
          FROM episode e LEFT JOIN addr_pt a ON a.address_key = e.address_key
          WHERE e.d > DATE '{asof}' - INTERVAL {CONTEXT_WEEKS * 7} DAY
        )
        SELECT pt.inspection_id, min(c.community_area) AS community_area
        FROM pt JOIN ca_geom c ON pt.lat IS NOT NULL AND ST_Contains(c.geom, ST_Point(pt.lon, pt.lat))
        GROUP BY 1
    """)


def pest_terms(vtext: str) -> list[str]:
    text = re.sub(PEST_HEADING, " ", vtext or "")
    text = re.sub(r"PEST CONTROL|PEST MANAGEMENT", " ", text)
    found = [name for name, rx in PEST_TERMS if re.search(rx, text)]
    return found or [GENERAL_TERM]


def general_only(terms: list[str]) -> bool:
    """Only the generic word 'pests' (or just the heading): typically an entry-point or harborage citation."""
    return all(t in ("pests", GENERAL_TERM) for t in terms)


def findings(con: duckdb.DuckDBPyConnection, asof: date) -> list[dict]:
    rows = q(
        con,
        f"""
        WITH cur AS (
          SELECT e.*, ca.community_area, ca2.name AS area_name
          FROM episode e
          LEFT JOIN episode_area ca ON ca.inspection_id = e.inspection_id
          LEFT JOIN ca_geom ca2 ON ca2.community_area = ca.community_area
          WHERE e.d > DATE '{asof}' - INTERVAL {BACKFILL_DAYS} DAY
        )
        SELECT c.inspection_id, c.d, c.dba, c.license_no, c.address_key, c.community_area, c.area_name,
          c.results, c.inspection_type, c.risk, c.vtext,
          (SELECT count(*) FROM pest_day p WHERE p.license_no = c.license_no
             AND p.d >= c.d - INTERVAL {HISTORY_DAYS} DAY AND p.d < c.d) AS pest_findings_2y,
          (SELECT count(*) FROM rest r WHERE r.license_no = c.license_no AND r.d > c.d) AS inspections_since,
          (SELECT {{'d': r.d, 'result': r.results, 'type': r.inspection_type}} FROM rest r
             WHERE r.license_no = c.license_no AND r.d > c.d
             ORDER BY r.d DESC, r.inspection_id DESC LIMIT 1) AS last_insp
        FROM cur c
        ORDER BY c.d DESC, c.license_no, c.inspection_id
    """,
    )
    return rows


def operator_groups(con: duckdb.DuckDBPyConnection, asof: date) -> dict[str, list[dict]]:
    """Active-looking restaurant licenses (inspected in the last 365 days) grouped by normalized DBA."""
    rows = q(
        con,
        f"""
        WITH act AS (
          SELECT license_no, first(dba ORDER BY d DESC, inspection_id DESC) AS dba,
            first(address_key ORDER BY d DESC, inspection_id DESC) AS address_key
          FROM rest WHERE d > DATE '{asof}' - INTERVAL {OPERATOR_DAYS} DAY GROUP BY 1
        ), pf AS (
          SELECT license_no, count(*) AS n FROM pest_day
          WHERE d > DATE '{asof}' - INTERVAL {OPERATOR_DAYS} DAY GROUP BY 1
        )
        SELECT a.license_no, a.dba, a.address_key, coalesce(pf.n, 0) AS pest_365
        FROM act a LEFT JOIN pf USING (license_no) ORDER BY a.license_no
    """,
    )
    groups: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        key = normalize(r["dba"])
        if key:
            groups[key].append(r)
    return groups


def operator_stats(row: dict, groups: dict[str, list[dict]]) -> tuple[int, int]:
    others = [
        g
        for g in groups.get(normalize(row["dba"]), [])
        if g["license_no"] != row["license_no"] and g["address_key"] != row["address_key"]
    ]
    return len(others), sum(g["pest_365"] for g in others)


# ----------------------------------------------------------------------------------------------------------
# Overture places
# ----------------------------------------------------------------------------------------------------------
def load_places(con: duckdb.DuckDBPyConnection) -> tuple[list[dict], list[dict], str]:
    cat = "coalesce(category, '') || ' ' || array_to_string(coalesce(categories, []), ' ')"
    rows = q(
        con,
        f"""
        SELECT id, name, category, phones, websites, emails, address, locality, postcode, confidence,
          {address_key_sql("address")} AS address_key,
          regexp_matches(lower({cat}), '{esc(PEST_COMPANY_RX)}') AS is_pest, release
        FROM places
        WHERE in_chicago AND status IS DISTINCT FROM 'permanently_closed' ORDER BY id
    """,
    )
    release = rows[0]["release"] if rows else ""
    by_addr: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_addr[r["address_key"]].append(r)
    pests = [r for r in rows if r["is_pest"]]
    return rows, pests, release


def match_contact(row: dict, by_addr: dict[str, list[dict]]) -> dict | None:
    key = normalize(row["dba"])
    best = None
    for p in by_addr.get(row["address_key"], []):
        if p["is_pest"]:
            continue
        phone, site = phone_of(p["phones"]), website_of(p["websites"])
        if not (phone or site):
            continue
        ratio = token_set_ratio(key, normalize(p["name"]))
        if ratio < NAME_MATCH_MIN:
            continue
        rank = (-ratio, -(p["confidence"] or 0), p["id"])
        if best is None or rank < best[0]:
            best = (rank, p, ratio, phone, site)
    if best is None:
        return None
    _, p, ratio, phone, site = best
    return {
        "placeName": p["name"],
        "phone": phone,
        "website": site,
        "source": SOURCE,
        "nameMatch": rnd(ratio, 2),
    }


def pest_companies(con: duckdb.DuckDBPyConnection, pests: list[dict]) -> list[dict]:
    licenses = q(
        con,
        f"""
        SELECT account_number, legal_name, dba, address_key, license_description, license_status
        FROM biz_licenses
        WHERE regexp_matches(upper(coalesce(license_description, '') || ' ' || coalesce(business_activity, '')),
                             '{esc(PEST_LICENSE_RX)}')
        ORDER BY account_number, license_id
    """,
    )
    lic_by_addr: dict[str, list[dict]] = defaultdict(list)
    for lic in licenses:
        lic_by_addr[lic["address_key"]].append(lic)

    seen: dict[str, dict] = {}
    for p in pests:
        phone, site = phone_of(p["phones"]), website_of(p["websites"])
        ident = web.base_host(web.host_of(site)) if site else (phone or f"id:{p['id']}")
        item = {
            "name": title(p["name"]),
            "address": ", ".join(x for x in (p["address"], p["locality"], p["postcode"]) if x) or None,
            "phone": phone,
            "website": site,
            "email": email_of(p["emails"]),
            "category": (p["category"] or "").replace("_", " ") or None,
            "licensedLegalName": None,
            "source": SOURCE,
            "_rank": (-(p["confidence"] or 0), p["id"]),
            "_key": normalize(p["name"]),
            "_addr": p["address_key"],
        }
        cur = seen.get(ident)
        if cur is None or item["_rank"] < cur["_rank"]:
            seen[ident] = item
    out = []
    for item in seen.values():
        for lic in lic_by_addr.get(item["_addr"], []):
            names = [normalize(lic["dba"]), normalize(lic["legal_name"])]
            if any(n and token_set_ratio(item["_key"], n) >= 0.9 for n in names):
                item["licensedLegalName"] = title(lic["legal_name"])
                break
        out.append({k: v for k, v in item.items() if not k.startswith("_")})
    return sorted(out, key=lambda r: ((r["name"] or "").lower(), r["address"] or "", r["phone"] or ""))


# ----------------------------------------------------------------------------------------------------------
def context(con: duckdb.DuckDBPyConnection, asof: date) -> dict:
    start = f"DATE '{asof}' - INTERVAL {CONTEXT_WEEKS * 7} DAY"
    ep = q(
        con,
        f"""
        SELECT count(*) AS n, count(*) FILTER (WHERE results = 'Fail') AS fails FROM episode WHERE d > {start}
    """,
    )[0]
    ordinary = q(
        con,
        f"""
        SELECT count(*) AS n, count(*) FILTER (WHERE results = 'Fail') AS fails FROM rest
        WHERE NOT f_pest AND {VALID_RESULT} AND d > {start}
    """,
    )[0]
    by_week = {
        r["i"]: r["n"]
        for r in q(
            con,
            f"""
        SELECT (DATE '{asof}' - d) // 7 AS i, count(*) AS n FROM episode WHERE d > {start} GROUP BY 1
    """,
        )
    }
    weekly = [by_week.get(i, 0) for i in range(CONTEXT_WEEKS - 1, -1, -1)]
    areas = q(
        con,
        f"""
        SELECT ea.community_area AS id, any_value(c.name) AS name, count(*) AS n
        FROM episode e JOIN episode_area ea ON ea.inspection_id = e.inspection_id
          JOIN ca_geom c ON c.community_area = ea.community_area
        WHERE e.d > {start} GROUP BY 1 ORDER BY n DESC, id LIMIT {TOP_AREAS}
    """,
    )
    located = q(
        con,
        f"SELECT count(*) AS n FROM episode e JOIN episode_area ea USING (inspection_id) WHERE e.d > {start}",
    )[0]["n"]
    n = ep["n"]
    texts = [
        r["vtext"] for r in q(con, f"SELECT vtext FROM episode WHERE d > {start} ORDER BY inspection_id")
    ]
    general = sum(1 for t in texts if general_only(pest_terms(t)))
    per_week = {
        r["i"]: r["n"]
        for r in q(
            con,
            f"SELECT (DATE '{asof}' - d) // 7 AS i, count(*) AS n FROM rest WHERE d > {start} GROUP BY 1",
        )
    }
    counts = sorted(per_week.get(i, 0) for i in range(CONTEXT_WEEKS))
    typical = (counts[len(counts) // 2 - 1] + counts[len(counts) // 2]) / 2
    return {
        "label": "Descriptive history, not a prediction",
        "weeks": CONTEXT_WEEKS,
        "windowStart": con.execute(f"SELECT ({start})::DATE").fetchone()[0].isoformat(),
        "episodes": n,
        "perWeek": rnd(n / CONTEXT_WEEKS, 1),
        "weeklyMin": min(weekly) if weekly else None,
        "weeklyMax": max(weekly) if weekly else None,
        "weekly": weekly,
        "failShare": rnd(ep["fails"] / n if n else None),
        "generalMentionOnlyShare": rnd(general / len(texts) if texts else None),
        "latestWeekInspections": per_week.get(0, 0),
        "typicalWeekInspections": rnd(typical, 1),
        "ordinaryInspections": ordinary["n"],
        "ordinaryFailShare": rnd(ordinary["fails"] / ordinary["n"] if ordinary["n"] else None),
        "areaLocated": located,
        "topAreas": [
            {"id": a["id"], "name": a["name"], "episodes": a["n"], "share": rnd(a["n"] / n if n else None)}
            for a in areas
        ],
    }


CSV_FIELDS = [
    "in_latest_week",
    "inspection_date",
    "restaurant",
    "address",
    "community_area",
    "result",
    "inspection_type",
    "risk",
    "pest_terms",
    "specific_pest_term",
    "pest_findings_prior_2y",
    "last_inspection_date",
    "last_inspection_result",
    "other_locations_same_name",
    "other_locations_pest_findings_365d",
    "phone",
    "website",
    "contact_source",
    "license_no",
    "inspection_id",
    "date_contacted",
    "outcome",
    "notes",
]


def csv_row(f: dict) -> dict:
    last = f["lastInspection"]
    c = f["contact"]
    return {
        "in_latest_week": "yes" if f["inLatestWeek"] else "no",
        "inspection_date": f["date"],
        "restaurant": f["restaurant"],
        "address": f["address"],
        "community_area": f["communityArea"]["name"] if f["communityArea"] else "",
        "result": f["result"],
        "inspection_type": f["inspectionType"],
        "risk": f["risk"] or "",
        "pest_terms": "; ".join(f["pestTerms"]),
        "specific_pest_term": "no" if f["pestTermsGeneralOnly"] else "yes",
        "pest_findings_prior_2y": f["pestFindings2y"],
        "last_inspection_date": last["date"] if last else "",
        "last_inspection_result": last["result"] if last else "",
        "other_locations_same_name": f["otherLocations"],
        "other_locations_pest_findings_365d": f["otherLocationsPest365"],
        "phone": (c or {}).get("phone") or "",
        "website": (c or {}).get("website") or "",
        "contact_source": (c or {}).get("source") or "",
        "license_no": f["licenseNo"],
        "inspection_id": f["inspectionId"],
        "date_contacted": "",
        "outcome": "",
        "notes": "",
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", type=Path, default=JSON_OUT, help=f"JSON path for the app (default {JSON_OUT})")
    ap.add_argument("--csv", type=Path, default=None, help="CSV path (default data/pest-<as-of>.csv)")
    args = ap.parse_args()

    con = db.connect()
    asof = con.execute("SELECT max(inspection_date) FROM food_inspections").fetchone()[0]
    build_tables(con, asof)
    groups = operator_groups(con, asof)
    place_rows, pests, release = load_places(con)
    by_addr: dict[str, list[dict]] = defaultdict(list)
    for p in place_rows:
        by_addr[p["address_key"]].append(p)

    week_start = asof.toordinal() - (WEEK_DAYS - 1)
    items = []
    for r in findings(con, asof):
        others, others_pest = operator_stats(r, groups)
        last = r["last_insp"]
        terms = pest_terms(r["vtext"])
        contact = match_contact(r, by_addr)
        items.append(
            {
                "inspectionId": r["inspection_id"],
                "date": r["d"].isoformat(),
                "inLatestWeek": r["d"].toordinal() >= week_start,
                "restaurant": title(r["dba"]),
                "licenseNo": r["license_no"],
                "address": title(r["address_key"]),
                "addressKey": r["address_key"],
                "communityArea": {"id": r["community_area"], "name": r["area_name"]}
                if r["community_area"]
                else None,
                "result": r["results"],
                "inspectionType": r["inspection_type"],
                "risk": r["risk"],
                "pestTerms": terms,
                "pestTermsGeneralOnly": general_only(terms),
                "pestFindings2y": r["pest_findings_2y"],
                "lastInspection": {
                    "date": last["d"].isoformat(),
                    "result": last["result"],
                    "type": last["type"],
                }
                if last
                else None,
                "inspectionsSince": r["inspections_since"],
                "otherLocations": others,
                "otherLocationsPest365": others_pest,
                "contact": contact,
            }
        )
    companies = pest_companies(con, pests)
    ctx = context(con, asof)

    week = [f for f in items if f["inLatestWeek"]]
    with_contact = [f for f in items if f["contact"]]
    out = {
        "generatedAt": asof.isoformat(),
        "asOf": asof.isoformat(),
        "definition": (
            "A fresh pest finding is a restaurant inspection (facility type Restaurant, result Pass, Pass w/ Conditions "
            "or Fail) whose violation text cites rodents, mice, rats, droppings, roaches, flies, insects or pests, at a "
            f"license with no pest finding in the previous {EPISODE_GAP_DAYS} days (the same episode definition as "
            f"signal-lab H23). The weekly list is the last {WEEK_DAYS} days of inspections through the as-of date; the "
            f"backfill list is the last {BACKFILL_DAYS} days. Pilot targeting list only: no probability of winning work "
            "is modelled."
        ),
        "windows": {
            "weekDays": WEEK_DAYS,
            "backfillDays": BACKFILL_DAYS,
            "episodeGapDays": EPISODE_GAP_DAYS,
            "historyDays": HISTORY_DAYS,
            "operatorDays": OPERATOR_DAYS,
        },
        "counts": {
            "latestWeek": len(week),
            "last28Days": len(items),
            "withContact": len(with_contact),
            "pestCompanies": len(companies),
        },
        "context": ctx,
        "findings": items,
        "pestCompanies": companies,
        "attribution": {
            "text": ATTRIBUTION,
            "overtureRelease": release,
            "contactMatch": f"Restaurant phone and website come from Overture Maps places at the same street address with a similar name (token-set ratio of at least {NAME_MATCH_MIN}); never guessed. Verify before use. {SOCIAL_NOTE}",
        },
    }
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(out, separators=(",", ":"), ensure_ascii=False) + "\n", encoding="utf-8")

    csv_path = args.csv or Path(f"data/pest-{asof}.csv")
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=CSV_FIELDS, lineterminator="\n")
        w.writeheader()
        for f in week:
            w.writerow(csv_row(f))

    rate = len(with_contact) / len(items) if items else 0.0
    print(
        f"pest pilot as of {asof}: {len(week)} rows in latest week, {len(items)} in {BACKFILL_DAYS} days "
        f"({len(with_contact)} with Overture contact, {rate:.1%}), {len(companies)} pest-control companies; "
        f"wrote {args.json} and {csv_path}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
