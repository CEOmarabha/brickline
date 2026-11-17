"""Build the client-facing lead snapshot from the warehouse.

    uv run python -m engine.leads.snapshot            # writes web/data/snapshot.json

Every probability shown to a client is a historical rate from the same records (Chicago, 2012 onward),
conditioned on how long ago the signal happened. Nothing is guessed: missing data stays missing.
"""

from __future__ import annotations

import argparse
import bisect
import json
import os
import re
import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from engine import db
from engine.score import licenses
from engine.score.food import (
    CLOSED,
    NAME_KEY,
    RENO_PREDICATE,
    SAME_NAME,
    closure_views,
)
from engine.score.signals import (
    CELL_LAT,
    CELL_LON,
    INVESTOR_RE,
    LIFT_STRONG,
    LIFT_USEFUL,
    LIFT_WEAK,
    MAJOR,
    NON_OPERATOR_RE,
    PARCEL_FEATURES,
    RESI_CLASSES,
    build_parcel_features,
    fit_combo_rates,
    one,
    prepare_base,
    q,
)
from engine.text import title

OUT = Path("web/data/snapshot.json")

# Client trades. `violation` = violation trade flag, `permit` = permit trade flag, `role` = permit party role
# of the contractor who does that work.
TRADES = {
    "porch": {"label": "Porches & decks", "violation": "porch", "permit": "porch", "role": "gc"},
    "masonry": {
        "label": "Masonry & tuckpointing",
        "violation": "masonry",
        "permit": "masonry",
        "role": "masonry",
    },
    "roofing": {"label": "Roofing", "violation": "roofing", "permit": "roofing", "role": "gc"},
    "plumbing": {"label": "Plumbing", "violation": "plumbing", "permit": "plumbing", "role": "plumbing"},
    "electrical": {
        "label": "Electrical",
        "violation": "electrical",
        "permit": "electrical",
        "role": "electrical",
    },
    "general": {
        "label": "General contracting & rehab",
        "violation": None,
        "permit": "interior_buildout",
        "role": "gc",
    },
}
OWNERS = ("individual", "company")
COMMERCIAL_SUB_TRADES = ("electrical", "plumbing", "hvac")
COMPLAINT_TRADES = ("porch", "masonry", "roofing", "general")
# A usable street address: number, optional direction, then a street name that is more than one letter.
COMPLETE_ADDRESS = "^[0-9]+( [NSEW])? [A-Z0-9]{2,}"
MIN_CELL = 300  # minimum historical episodes per cell before a finer split is used

# Assumptions surfaced in the UI (replace with pilot data).
WIN_RATE = {"individual": 0.05, "company": 0.10}
MARGIN = 0.30

COMPANY_SQL = f"regexp_matches(upper(coalesce({{col}}, '')), '{INVESTOR_RE}')"
SEGMENT_SQL = """
  CASE
    WHEN class IN ('202','203','204','205','206','207','208','209','210','234','278','295') THEN 'single-family'
    WHEN class IN ('211','212') THEN '2-6 unit flat'
    WHEN class LIKE '3%' OR class LIKE '9%' THEN 'apartment 7+'
    WHEN class LIKE '5%' OR class LIKE '6%' OR class LIKE '7%' OR class LIKE '8%' THEN 'commercial/industrial'
    ELSE NULL
  END
"""


def cdf_points(days: list[float]) -> list[float]:
    """Sorted conversion delays (days) — used to compute the share of conversions already past."""
    return sorted(d for d in days if d is not None)


def share_by(points: list[float], age: float) -> float:
    if not points:
        return 0.0
    return bisect.bisect_right(points, age) / len(points)


def remaining_probability(p: float, points: list[float], age: float) -> float:
    """P(conversion within the window | no conversion observed by `age` days)."""
    f = share_by(points, age)
    denom = 1 - p * f
    return max(0.0, p * (1 - f) / denom) if denom > 0 else 0.0


def adjusted(age: int) -> str:
    """Closing clause of a probability basis: the rate is conditioned on the time already passed."""
    if age == 0:
        return "signal is from today, so no time adjustment"
    return f"adjusted for the {age} day{'' if age == 1 else 's'} already passed"


def iso(d) -> str | None:
    return d.isoformat() if d else None


def generated_at(dates: dict) -> str:
    """Reproducible build stamp: the newest source record (midnight UTC), or SNAPSHOT_GENERATED_AT if set.

    A wall-clock time would make two builds from the same warehouse differ, which defeats md5 comparisons.
    """
    override = os.environ.get("SNAPSHOT_GENERATED_AT")
    if override:
        return override
    newest = max(d for d in dates.values() if d)
    return datetime(newest.year, newest.month, newest.day, tzinfo=UTC).isoformat(timespec="seconds")


ENTITY_STOPWORDS = {"LLC", "INC", "CORP", "CO", "THE", "OF", "AND", "LTD", "LP", "TRUST", "SERIES", "GROUP"}


def same_entity(a: str | None, b: str | None) -> bool:
    """Loose match between a buyer name and a tax-roll owner name (the roll lags sales by months)."""
    if not a or not b:
        return False

    def tokens(s: str) -> set[str]:
        return {t for t in re.sub(r"[^A-Z0-9 ]", " ", s.upper()).split() if len(t) > 2} - ENTITY_STOPWORDS

    return bool(tokens(a) & tokens(b))


# ----------------------------------------------------------------------------------------------------------
def prepare(con) -> date:
    """Base tables plus address -> community area (point in polygon), parcel -> area, ZIP -> area fallback."""
    prepare_base(con)
    con.execute("INSTALL spatial; LOAD spatial;")
    con.execute("""
        CREATE OR REPLACE TEMP TABLE ca_geom AS
        SELECT community_area, ST_GeomFromText(geom_wkt) AS geom FROM community_areas
    """)
    con.execute("""
        CREATE OR REPLACE TEMP TABLE addr_area AS
        WITH pts AS (
          SELECT address_key, median(lat) AS lat, median(lon) AS lon FROM (
            SELECT address_key, lat, lon FROM permits WHERE lat IS NOT NULL
            UNION ALL SELECT address_key, lat, lon FROM violations WHERE lat IS NOT NULL
          ) WHERE address_key IS NOT NULL GROUP BY 1
        )
        SELECT pts.address_key, min(c.community_area) AS community_area
        FROM pts JOIN ca_geom c ON ST_Contains(c.geom, ST_Point(pts.lon, pts.lat))
        GROUP BY 1
    """)
    con.execute("""
        CREATE OR REPLACE TEMP TABLE pin_area AS
        SELECT pin10, first(community_area ORDER BY n DESC, community_area) AS community_area FROM (
          SELECT x.pin10, aa.community_area, count(*) AS n FROM (
            SELECT pin10, address_key FROM p WHERE pin10 IS NOT NULL
            UNION ALL SELECT pin10, address_key FROM parcels
          ) x JOIN addr_area aa USING (address_key) GROUP BY ALL
        ) GROUP BY pin10
    """)
    con.execute("""
        CREATE OR REPLACE TEMP TABLE zip_area AS
        SELECT zip, first(community_area ORDER BY n DESC, community_area) AS community_area FROM (
          SELECT par.zip, aa.community_area, count(*) AS n
          FROM parcels par JOIN addr_area aa USING (address_key) WHERE par.zip IS NOT NULL GROUP BY ALL
        ) GROUP BY zip
    """)
    # Parcel facts for an address: direct address match, else via the address's most common permit parcel.
    con.execute("""
        CREATE OR REPLACE TEMP TABLE addr_parcel AS
        SELECT address_key, min(pin10) AS pin10 FROM parcels WHERE address_key IS NOT NULL GROUP BY 1
        UNION ALL
        SELECT a.address_key, a.pin10 FROM addr_pin a
        WHERE NOT EXISTS (SELECT 1 FROM parcels x WHERE x.address_key = a.address_key)
    """)
    # Block grid: one point per address, per parcel, and the residential parcels in each cell.
    con.execute("""
        CREATE OR REPLACE TEMP TABLE addr_pt AS
        SELECT address_key, median(lat) AS lat, median(lon) AS lon FROM (
          SELECT address_key, lat, lon FROM permits WHERE lat IS NOT NULL
          UNION ALL SELECT address_key, lat, lon FROM violations WHERE lat IS NOT NULL
          UNION ALL SELECT address_key, lat, lon FROM sr311 WHERE lat IS NOT NULL
        ) WHERE address_key IS NOT NULL AND lat BETWEEN 41.6 AND 42.1 AND lon BETWEEN -87.95 AND -87.5
        GROUP BY 1
    """)
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE resi AS
        SELECT r.pin10, pt.cy, pt.cx FROM res_chars r JOIN (
          SELECT x.pin10, floor(median(a.lat) / {CELL_LAT})::BIGINT AS cy, floor(median(a.lon) / {CELL_LON})::BIGINT AS cx
          FROM (
            SELECT pin10, address_key FROM parcels WHERE address_key IS NOT NULL
            UNION ALL SELECT pin10, address_key FROM addr_pin
          ) x JOIN addr_pt a USING (address_key) GROUP BY 1
        ) pt USING (pin10)
        WHERE r.class IN {RESI_CLASSES}
    """)
    return one(con, "SELECT max(issue_date) AS d FROM permits")["d"]


def as_of(con) -> dict:
    return one(
        con,
        """
        SELECT (SELECT max(issue_date) FROM permits) AS permits,
               (SELECT max(violation_date) FROM violations) AS violations,
               (SELECT max(sale_date) FROM sales) AS sales,
               (SELECT max(created_date) FROM sr311) AS complaints,
               (SELECT max(inspection_date) FROM food_inspections) AS foodInspections
    """,
    )


# ----------------------------------------------------------------------------------------------------------
def summarize(days: list[int | None]) -> dict:
    """Episode count, conversion rate and sorted delays (days) for one outcome; None = no conversion."""
    delays = cdf_points(days)
    return {"episodes": len(days), "p": len(delays) / len(days) if days else 0.0, "delays": delays}


def violation_model(con) -> dict:
    """Per trade and owner type: P(matching permit within 365 days) and delay distribution, 2012–2025.

    Masonry is also split by building age (masonry walls built before 1910 vs other): `age` holds that split and
    `cells` the owner x age split, which is used only when every cell has at least MIN_CELL episodes.
    """
    model = {}
    for key, t in TRADES.items():
        vt = t["violation"]
        if not vt:
            continue
        rows = q(
            con,
            f"""
            WITH ep AS (
              SELECT address_key, violation_date FROM (
                SELECT address_key, violation_date,
                  lag(violation_date) OVER (PARTITION BY address_key ORDER BY violation_date) AS prev
                FROM (SELECT DISTINCT address_key, violation_date FROM violations
                      WHERE t_{vt} AND violation_date BETWEEN DATE '2012-01-01' AND DATE '2025-10-31')
              ) WHERE prev IS NULL OR violation_date - prev > 365
            ),
            o AS (
              SELECT ep.*, coalesce({COMPANY_SQL.format(col="par.owner_name")}, false) AS company,
                coalesce(rc.ext_wall = 'Masonry' AND rc.year_built < 1910, false) AS old_masonry
              FROM ep LEFT JOIN addr_parcel ap ON ap.address_key = ep.address_key
              LEFT JOIN parcels par ON par.pin10 = ap.pin10
              LEFT JOIN res_chars rc ON rc.pin10 = ap.pin10
            )
            SELECT o.company, o.old_masonry,
              min(p.issue_date - o.violation_date) AS days
            FROM o LEFT JOIN p ON p.address_key = o.address_key AND p.t_{t["permit"]}
              AND p.issue_date > o.violation_date AND p.issue_date <= o.violation_date + INTERVAL 365 DAY
            GROUP BY o.address_key, o.violation_date, o.company, o.old_masonry
        """,
        )
        entry = {
            owner: summarize([r["days"] for r in rows if r["company"] == (owner == "company")])
            for owner in ("individual", "company")
        }
        if key == "masonry":
            ages = (("pre1910", True), ("other", False))
            entry["age"] = {
                age: summarize([r["days"] for r in rows if r["old_masonry"] == f]) for age, f in ages
            }
            entry["cells"] = {
                (owner, age): summarize(
                    [
                        r["days"]
                        for r in rows
                        if r["old_masonry"] == f and r["company"] == (owner == "company")
                    ]
                )
                for owner in ("individual", "company")
                for age, f in ages
            }
            entry["use_cells"] = all(c["episodes"] >= MIN_CELL for c in entry["cells"].values())
        model[key] = entry
    return model


def sale_model(con) -> dict:
    """Investor purchases: per segment, P(trade permit within 365 days) and delay distribution, 2012–mid 2025."""
    flags = ", ".join(f"bool_or(p.t_{t['permit']}) AS {k}" for k, t in TRADES.items())
    rows = q(
        con,
        f"""
        WITH s AS (
          SELECT pin10, sale_date, {SEGMENT_SQL} AS segment FROM sales
          WHERE NOT filtered_out AND NOT is_multisale
            AND sale_date BETWEEN DATE '2012-01-01' AND DATE '2025-06-30'
            AND {COMPANY_SQL.format(col="buyer_name")}
            AND NOT regexp_matches(upper(coalesce(buyer_name, '')), '{NON_OPERATOR_RE}')
        )
        SELECT s.segment, s.pin10, s.sale_date, {flags},
          bool_or({MAJOR.replace("permit_type", "p.permit_type").replace("reported_cost", "p.reported_cost")})
            AS major,
          min(p.issue_date - s.sale_date) AS first_days
        FROM s LEFT JOIN p ON p.pin10 = s.pin10
          AND p.issue_date > s.sale_date AND p.issue_date <= s.sale_date + INTERVAL 365 DAY
        WHERE s.segment IS NOT NULL
        GROUP BY ALL
    """,
    )
    model = {}
    for seg in ("single-family", "2-6 unit flat", "apartment 7+", "commercial/industrial"):
        sub = [r for r in rows if r["segment"] == seg]
        if not sub:
            continue
        model[seg] = {
            "purchases": len(sub),
            "p_any": sum(r["first_days"] is not None for r in sub) / len(sub),
            "p_major": sum(bool(r["major"]) for r in sub) / len(sub),
            "p_trade": {k: sum(bool(r[k]) for r in sub) / len(sub) for k in TRADES},
            "delays": cdf_points([r["first_days"] for r in sub]),
        }
    return model


def job_values(con, today: date) -> dict:
    out = {}
    for k, t in TRADES.items():
        r = one(
            con,
            f"""
            SELECT median(reported_cost) AS v FROM p
            WHERE t_{t["permit"]} AND NOT {MAJOR} AND reported_cost > 0
              AND issue_date > DATE '{today}' - INTERVAL 730 DAY
        """,
        )
        out[k] = float(r["v"] or 0)
    return out


# ----------------------------------------------------------------------------------------------------------
AGE_SEGMENT = {
    "pre1910": "buildings with masonry walls built before 1910",
    "other": "other buildings (frame, newer or unknown construction)",
}


def building_evidence(r: dict) -> list[dict]:
    """Assessor facts (year built, exterior walls) when the parcel has them."""
    out = []
    if r.get("year_built"):
        out.append({"label": "Year built", "value": str(r["year_built"])})
    if r.get("ext_wall"):
        out.append({"label": "Exterior walls", "value": r["ext_wall"]})
    return out


def violation_leads(con, today: date, vmodel: dict, values: dict) -> tuple[list[dict], list[dict]]:
    leads, won = [], []
    for key, t in TRADES.items():
        vt = t["violation"]
        if not vt:
            continue
        rows = q(
            con,
            f"""
            WITH recent AS (
              SELECT * FROM violations
              WHERE t_{vt} AND violation_date > DATE '{today}' - INTERVAL 150 DAY
            ),
            ep AS (
              SELECT address_key, min(violation_date) AS first_date, max(violation_date) AS last_date,
                     list(DISTINCT description ORDER BY description) AS descriptions, min(id) AS violation_id,
                     bool_or(violation_status = 'OPEN') AS any_open,
                     count(*) AS citations, min(inspection_category) AS category,
                     median(lat) AS lat, median(lon) AS lon
              FROM recent GROUP BY address_key
            ),
            fresh AS (
              SELECT ep.* FROM ep
              WHERE NOT EXISTS (
                SELECT 1 FROM violations v WHERE v.address_key = ep.address_key AND v.t_{vt}
                  AND v.violation_date < ep.first_date AND v.violation_date >= ep.first_date - INTERVAL 365 DAY)
            )
            SELECT f.*, par.address, par.owner_name, par.owner_mailing, par.units, par.pin10,
              rc.year_built, rc.ext_wall,
              coalesce(ca.community_area, aa.community_area, pa.community_area, za.community_area)
                AS community_area,
              coalesce({COMPANY_SQL.format(col="par.owner_name")}, false) AS company,
              (SELECT min(p.issue_date) FROM p WHERE p.address_key = f.address_key AND p.t_{t["permit"]}
                 AND p.issue_date > f.first_date) AS permit_date,
              (SELECT first(pp.name_raw ORDER BY p.issue_date, p.id, pp.slot, pp.name_raw) FROM p
                 JOIN permit_parties pp ON pp.permit_id = p.id AND pp.role = '{t["role"]}'
                 WHERE p.address_key = f.address_key AND p.t_{t["permit"]} AND p.issue_date > f.first_date)
                AS permit_contractor
            FROM fresh f
            LEFT JOIN addr_parcel ap ON ap.address_key = f.address_key
            LEFT JOIN parcels par ON par.pin10 = ap.pin10
            LEFT JOIN res_chars rc ON rc.pin10 = ap.pin10
            LEFT JOIN ca_geom ca ON f.lat IS NOT NULL AND ST_Contains(ca.geom, ST_Point(f.lon, f.lat))
            LEFT JOIN addr_area aa ON aa.address_key = f.address_key
            LEFT JOIN pin_area pa ON pa.pin10 = ap.pin10
            LEFT JOIN zip_area za ON za.zip = par.zip
            ORDER BY f.first_date DESC, f.address_key
        """,
        )
        for r in rows:
            owner_type = "company" if r["company"] else "individual"
            m = vmodel[key][owner_type]
            segment = f"{owner_type}-owned properties"
            if key == "masonry":
                old = r["ext_wall"] == "Masonry" and r["year_built"] is not None and r["year_built"] < 1910
                age_key = "pre1910" if old else "other"
                if vmodel[key]["use_cells"]:
                    m = vmodel[key]["cells"][(owner_type, age_key)]
                    segment = f"{owner_type}-owned " + AGE_SEGMENT[age_key]
                else:
                    m = vmodel[key]["age"][age_key]
                    segment = AGE_SEGMENT[age_key]
            age = (today - r["first_date"]).days
            base = {
                "trade": key,
                "address": title(r["address"] or r["address_key"]),
                "communityArea": r["community_area"],
                "signalDate": iso(r["first_date"]),
            }
            if r["permit_date"]:
                won.append(
                    base
                    | {
                        "permitDate": iso(r["permit_date"]),
                        "contractor": title(r["permit_contractor"]),
                        "daysToPermit": (r["permit_date"] - r["first_date"]).days,
                    }
                )
                continue
            if not r["any_open"]:
                continue
            p_rem = remaining_probability(m["p"], m["delays"], age)
            ev = p_rem * WIN_RATE[owner_type] * values[key] * MARGIN
            tier = "act_now" if age <= 14 else "this_week" if age <= 45 else "monitor"
            leads.append(
                base
                | {
                    "id": f"v-{key}-{r['violation_id']}",
                    "kind": "violation",
                    "trades": [key],
                    "title": f"{TRADES[key]['label']} repair ordered",
                    "ageDays": age,
                    "tier": tier,
                    "probability": round(p_rem, 4),
                    "probabilityBasis": (
                        f"{m['p'] * 100:.1f}% of similar {TRADES[key]['label'].lower()} violations at "
                        f"{segment} led to a permitted repair within a year "
                        f"({m['episodes']:,} cases, 2012–2025); {adjusted(age)}."
                    ),
                    "expectedValue": round(ev, 2),
                    "jobValue": values[key],
                    "owner": {
                        "name": title(r["owner_name"]),
                        "type": owner_type,
                        "mailing": title(r["owner_mailing"]),
                        "units": r["units"],
                    },
                    "evidence": [
                        {"label": "First cited", "value": iso(r["first_date"])},
                        {"label": "Citations in last 150 days", "value": str(r["citations"])},
                        {"label": "Inspection type", "value": title(r["category"]) or "—"},
                        *[{"label": "Violation", "value": d.capitalize()} for d in r["descriptions"][:3]],
                        *building_evidence(r),
                    ],
                    "action": (
                        "Send a letter to the owner's mailing address this week, then follow up at weeks 6, 12 and 24."
                        if owner_type == "individual"
                        else "Company-owned: look up the owner's business contact and call or email; mail as backup."
                    ),
                    "sourceUrl": (
                        "https://data.cityofchicago.org/resource/22u3-xenr.json?id=" + str(r["violation_id"])
                    ),
                }
            )
    return leads, won


def investor_leads(con, today: date, today_sales: date, smodel: dict) -> list[dict]:
    rows = q(
        con,
        f"""
        WITH s AS (
          SELECT *, {SEGMENT_SQL} AS segment,
                 regexp_replace(upper(trim(buyer_name)), '[^A-Z0-9 ]', '', 'g') AS buyer_key
          FROM sales
          WHERE NOT filtered_out AND NOT is_multisale AND {COMPANY_SQL.format(col="buyer_name")}
            AND NOT regexp_matches(upper(coalesce(buyer_name, '')), '{NON_OPERATOR_RE}')
        ),
        recent AS (
          -- Condo units share a pin10, so one lead per parcel and date (lead ids are pin10 + date).
          SELECT * FROM s WHERE sale_date > DATE '{today_sales}' - INTERVAL 240 DAY AND segment IS NOT NULL
          QUALIFY row_number() OVER (
            PARTITION BY pin10, sale_date ORDER BY sale_price DESC NULLS LAST, pin, buyer_name, seller_name) = 1
        ),
        repeat AS (
          SELECT buyer_key, count(*) AS purchases_24m FROM s
          WHERE sale_date > DATE '{today_sales}' - INTERVAL 730 DAY GROUP BY 1
        ),
        used AS (
          SELECT s.buyer_key, pp.name_raw, count(DISTINCT p.id) AS jobs
          FROM s JOIN p ON p.pin10 = s.pin10 AND p.issue_date > s.sale_date
            AND p.issue_date <= s.sale_date + INTERVAL 540 DAY
          JOIN permit_parties pp ON pp.permit_id = p.id AND pp.role = 'gc'
          WHERE s.buyer_key IN (SELECT buyer_key FROM recent)
          GROUP BY ALL
        )
        SELECT r.pin10, r.sale_date, r.sale_price, r.class, r.segment, r.buyer_name, r.buyer_key, r.seller_name,
          par.address, par.owner_name, par.owner_mailing, par.units,
          coalesce(pa.community_area, za.community_area) AS community_area,
          rp.purchases_24m,
          (SELECT list({{'name': name_raw, 'jobs': jobs}} ORDER BY jobs DESC, name_raw)[:3] FROM used u
             WHERE u.buyer_key = r.buyer_key) AS contractors_used,
          (SELECT list(par2.address ORDER BY s2.sale_date DESC, s2.pin10)[:5] FROM s s2
             JOIN parcels par2 ON par2.pin10 = s2.pin10
             WHERE s2.buyer_key = r.buyer_key AND s2.pin10 <> r.pin10
               AND s2.sale_date > DATE '{today_sales}' - INTERVAL 730 DAY) AS other_properties,
          (SELECT list({{'date': p.issue_date, 'type': p.permit_type, 'cost': p.reported_cost,
                         'description': left(p.description, 140)}} ORDER BY p.issue_date, p.id)[:3]
             FROM p WHERE p.pin10 = r.pin10 AND p.issue_date > r.sale_date) AS permits_since
        FROM recent r
        LEFT JOIN parcels par ON par.pin10 = r.pin10
        LEFT JOIN pin_area pa ON pa.pin10 = r.pin10
        LEFT JOIN zip_area za ON za.zip = par.zip
        LEFT JOIN repeat rp ON rp.buyer_key = r.buyer_key
        ORDER BY r.sale_date DESC, r.pin10, r.buyer_key
    """,
    )
    leads = []
    for r in rows:
        m = smodel.get(r["segment"])
        if not m:
            continue
        # Elapsed time is measured to today: permits are current even though sales publish late.
        age = (today - r["sale_date"]).days
        started = bool(r["permits_since"])
        p_any = 1.0 if started else remaining_probability(m["p_any"], m["delays"], age)
        repeat = r["purchases_24m"] or 1
        tier = (
            "act_now" if repeat >= 3 and not started else "this_week" if age <= 180 or started else "monitor"
        )
        trade_probs = {k: round(v, 4) for k, v in m["p_trade"].items()}
        leads.append(
            {
                "id": f"s-{r['pin10']}-{r['sale_date']}",
                "kind": "investor_purchase",
                "trades": list(TRADES),
                "trade": None,
                "title": "Renovation underway after investor purchase" if started else "Investor purchase",
                "address": title(r["address"]) or f"PIN {r['pin10']}",
                "communityArea": r["community_area"],
                "signalDate": iso(r["sale_date"]),
                "ageDays": age,
                "tier": tier,
                "probability": round(p_any, 4),
                "probabilityBasis": (
                    "A permit has already been issued since the purchase."
                    if started
                    else f"{m['p_any'] * 100:.1f}% of company purchases of {r['segment']} properties pulled a permit "
                    f"within a year ({m['purchases']:,} purchases, 2012–2025); {adjusted(age)}."
                ),
                "tradeProbabilities": trade_probs,
                "majorProbability": round(m["p_major"], 4),
                "segment": r["segment"],
                "salePrice": r["sale_price"],
                "buyer": {
                    "name": title(r["buyer_name"]),
                    "purchases24m": repeat,
                    "otherProperties": [title(a) for a in (r["other_properties"] or [])],
                    "contractorsUsed": [
                        {"name": title(c["name"]), "jobs": c["jobs"]} for c in (r["contractors_used"] or [])
                    ],
                },
                "owner": (
                    {
                        "name": title(r["owner_name"]),
                        "type": "company",
                        "mailing": title(r["owner_mailing"]),
                        "units": r["units"],
                    }
                    if same_entity(r["owner_name"], r["buyer_name"])
                    else {
                        "name": title(r["buyer_name"]),
                        "type": "company",
                        "mailing": None,
                        "units": r["units"],
                        "note": "The county tax roll has not caught up with this sale yet; research the buyer directly.",
                    }
                ),
                "permitsSince": [
                    {
                        "date": iso(x["date"]),
                        "type": title(x["type"].replace("PERMIT - ", "")),
                        "cost": x["cost"],
                        "description": (x["description"] or "").capitalize(),
                    }
                    for x in (r["permits_since"] or [])
                ],
                "evidence": [
                    {"label": "Sale date", "value": iso(r["sale_date"])},
                    {"label": "Sale price", "value": f"${r['sale_price']:,.0f}" if r["sale_price"] else "—"},
                    {"label": "Property type", "value": r["segment"]},
                    {"label": "Buyer purchases (24 months)", "value": str(repeat)},
                    {"label": "Seller", "value": title(r["seller_name"]) or "—"},
                ],
                "action": (
                    "Repeat investor: research the company (Illinois business registry, website) and call to "
                    "offer your crew for this and future properties."
                    if repeat >= 3
                    else "Research the buying company and reach out by email or phone; mail the owner address as backup."
                ),
                "sourceUrl": f"https://datacatalog.cookcountyil.gov/resource/wvhk-k5uv.json?pin={r['pin10']}0000",
            }
        )
    return leads


# ----------------------------------------------------------------------------------------------------------
# 311 signals (signal lab H07, H08, H09)
# ----------------------------------------------------------------------------------------------------------
def sr_signal(sr_type: str, by_pin: bool = False) -> str:
    """(k, d) rows for one 311 request type, keyed by address or by parcel (addr_pin)."""
    if by_pin:
        return (
            f"SELECT a.pin10 AS k, s.created_date AS d FROM sr311 s JOIN addr_pin a USING (address_key) "
            f"WHERE s.sr_type = '{sr_type}' AND NOT s.duplicate"
        )
    return (
        f"SELECT address_key AS k, created_date AS d FROM sr311 "
        f"WHERE sr_type = '{sr_type}' AND NOT duplicate AND address_key IS NOT NULL"
    )


def episodes_sql(signal_sql: str, start: str, end: str) -> str:
    """One episode (k, d) per key whenever 365+ days passed since its previous signal, as in the signal lab."""
    return f"""
        SELECT k, d FROM (
          SELECT k, d, lag(d) OVER (PARTITION BY k ORDER BY d) AS prev
          FROM (SELECT DISTINCT k, d FROM ({signal_sql}) WHERE k IS NOT NULL AND d BETWEEN DATE '{start}' AND DATE '{end}')
        ) WHERE prev IS NULL OR d - prev > 365
    """


def years(rows: list[dict]) -> str:
    return f"{min(r['d'] for r in rows).year}–{max(r['d'] for r in rows).year}"


def median_days(delays: list[int]) -> int | None:
    return int(delays[len(delays) // 2]) if delays else None


def complaint_model(con) -> dict:
    """'Building Violation' 311 complaints: P(violation within 120 days) and P(trade permit within 365 days)."""
    flags = ", ".join(
        f"min(p.issue_date - e.d) FILTER (WHERE p.t_{TRADES[k]['permit']}) AS {k}" for k in COMPLAINT_TRADES
    )
    rows = q(
        con,
        f"""
        WITH e AS ({episodes_sql(sr_signal("Building Violation"), "2016-01-01", "2025-06-30")}),
        v AS (
          SELECT e.k, e.d, min(x.violation_date - e.d) AS violation FROM e
          JOIN violations x ON x.address_key = e.k AND x.violation_date > e.d
            AND x.violation_date <= e.d + INTERVAL 120 DAY GROUP BY ALL
        ),
        pm AS (
          SELECT e.k, e.d, {flags} FROM e
          JOIN p ON p.address_key = e.k AND p.issue_date > e.d AND p.issue_date <= e.d + INTERVAL 365 DAY
          GROUP BY ALL
        )
        SELECT e.d, v.violation, pm.* EXCLUDE (k, d) FROM e
        LEFT JOIN v USING (k, d) LEFT JOIN pm USING (k, d)
    """,
    )
    return {
        "period": years(rows),
        "violation": summarize([r["violation"] for r in rows]),
        "trades": {k: summarize([r[k] for r in rows]) for k in COMPLAINT_TRADES},
    }


def porch_request_model(con) -> dict:
    rows = q(
        con,
        f"""
        WITH e AS ({episodes_sql(sr_signal("Porch Inspection Request"), "2016-01-01", "2025-06-30")})
        SELECT e.d, min(p.issue_date - e.d) AS days FROM e
        LEFT JOIN p ON p.address_key = e.k AND p.t_porch AND p.issue_date > e.d
          AND p.issue_date <= e.d + INTERVAL 365 DAY
        GROUP BY e.k, e.d
    """,
    )
    return {"period": years(rows), "porch": summarize([r["days"] for r in rows])}


def vacant_model(con, permit_end: str = "2024-10-31") -> dict:
    """Vacant/abandoned complaints per parcel: P(sale within 365 days), P(trade permit within 730 days).

    Permit outcomes only use episodes old enough (`permit_end`) for the 730-day window to be observed.
    """
    flags = ", ".join(
        f"min(p.issue_date - e.d) FILTER (WHERE p.t_{t['permit']}) AS {k}" for k, t in TRADES.items()
    )
    rows = q(
        con,
        f"""
        WITH e AS ({episodes_sql(sr_signal("Vacant/Abandoned Building Complaint", by_pin=True), "2016-01-01", "2025-06-30")}),
        sl AS (
          SELECT e.k, e.d, min(s.sale_date - e.d) AS sale FROM e
          JOIN sales s ON s.pin10 = e.k AND NOT s.filtered_out AND s.sale_date > e.d
            AND s.sale_date <= e.d + INTERVAL 365 DAY GROUP BY ALL
        ),
        pm AS (
          SELECT e.k, e.d, {flags} FROM e
          JOIN p ON p.pin10 = e.k AND p.issue_date > e.d AND p.issue_date <= e.d + INTERVAL 730 DAY
          GROUP BY ALL
        )
        SELECT e.d, sl.sale, pm.* EXCLUDE (k, d) FROM e
        LEFT JOIN sl USING (k, d) LEFT JOIN pm USING (k, d)
    """,
    )
    mature = [r for r in rows if r["d"] <= date.fromisoformat(permit_end)]
    return {
        "period": years(rows),
        "sale": summarize([r["sale"] for r in rows]),
        "permitPeriod": years(mature),
        "trades": {k: summarize([r[k] for r in mature]) for k in TRADES},
    }


def sr_rows(
    con, sr_type: str, today: date, days: int, skip: str, extra: str = "", by_pin: bool = False
) -> list[dict]:
    """Recent 311 requests of one type, one row per address (or parcel) that is still unresolved.

    A request starts an episode only if none came in the prior 365 days (the model's definition). `skip` is a
    SQL condition on `f` that drops leads where the follow-up event already happened.
    """
    join = "JOIN addr_pin a USING (address_key)" if by_pin else ""
    k = "a.pin10" if by_pin else "s.address_key"
    return q(
        con,
        f"""
        WITH recent AS (
          SELECT {k} AS k, s.address_key, s.created_date, s.sr_number, s.status, s.lat, s.lon
          FROM sr311 s {join}
          WHERE s.sr_type = '{sr_type}' AND NOT s.duplicate AND s.address_key IS NOT NULL
            AND s.created_date > DATE '{today}' - INTERVAL {days} DAY
        ),
        history AS ({sr_signal(sr_type, by_pin)}),
        ep AS (
          SELECT k, first(address_key ORDER BY created_date, sr_number) AS address_key,
                 min(created_date) AS first_date, count(*) AS requests,
                 first(sr_number ORDER BY created_date, sr_number) AS sr_number,
                 first(status ORDER BY created_date, sr_number) AS status, median(lat) AS lat, median(lon) AS lon
          FROM recent GROUP BY k
        ),
        f AS (
          SELECT ep.* FROM ep WHERE NOT EXISTS (
            SELECT 1 FROM history h WHERE h.k = ep.k AND h.d < ep.first_date AND h.d >= ep.first_date - INTERVAL 365 DAY)
        )
        SELECT f.*, par.address, par.owner_name, par.owner_mailing, par.units, rc.year_built, rc.ext_wall,
          coalesce(ca.community_area, aa.community_area, pa.community_area, za.community_area) AS community_area,
          coalesce({COMPANY_SQL.format(col="par.owner_name")}, false) AS company
          {extra}
        FROM f
        LEFT JOIN addr_parcel ap ON ap.address_key = f.address_key
        LEFT JOIN parcels par ON par.pin10 = ap.pin10
        LEFT JOIN res_chars rc ON rc.pin10 = ap.pin10
        LEFT JOIN ca_geom ca ON f.lat IS NOT NULL AND ST_Contains(ca.geom, ST_Point(f.lon, f.lat))
        LEFT JOIN addr_area aa ON aa.address_key = f.address_key
        LEFT JOIN pin_area pa ON pa.pin10 = ap.pin10
        LEFT JOIN zip_area za ON za.zip = par.zip
        WHERE {skip}
        ORDER BY f.first_date DESC, f.sr_number
    """,
    )


def requests_evidence(r: dict, days: int) -> list[dict]:
    """Repeat requests are a stronger signal; a single request is implied by the lead itself."""
    return (
        [{"label": f"311 requests (last {days} days)", "value": str(r["requests"])}]
        if r["requests"] > 1
        else []
    )


def sr_lead(r: dict, today: date, kind: str, id_prefix: str, tiers: tuple[int, int]) -> dict:
    """Fields shared by all 311-based leads."""
    age = (today - r["first_date"]).days
    owner_type = "company" if r["company"] else "individual"
    return {
        "id": f"{id_prefix}-{r['sr_number']}",
        "kind": kind,
        "address": title(r["address"] or r["address_key"]),
        "communityArea": r["community_area"],
        "signalDate": iso(r["first_date"]),
        "ageDays": age,
        "tier": "act_now" if age <= tiers[0] else "this_week" if age <= tiers[1] else "monitor",
        "owner": {
            "name": title(r["owner_name"]),
            "type": owner_type,
            "mailing": title(r["owner_mailing"]),
            "units": r["units"],
        },
        "sourceUrl": f"https://data.cityofchicago.org/resource/v6vf-nfxy.json?sr_number={r['sr_number']}",
    }


def owner_action(r: dict, individual: str) -> str:
    if not r["owner_mailing"]:
        return "No owner mailing address on file: look the owner up in Cook County records before mailing."
    if r["company"]:
        return "Company-owned: look up the owner's business contact and call or email; mail as backup."
    return individual


def complaint_leads(con, today: date, cmodel: dict) -> list[dict]:
    permit_flags = ", ".join(
        f"EXISTS (SELECT 1 FROM p WHERE p.address_key = f.address_key AND p.t_{TRADES[k]['permit']} "
        f"AND p.issue_date > f.first_date) AS done_{k}"
        for k in COMPLAINT_TRADES
    )
    rows = sr_rows(
        con,
        "Building Violation",
        today,
        60,
        "NOT EXISTS (SELECT 1 FROM violations v WHERE v.address_key = f.address_key AND v.violation_date > f.first_date)",
        extra=f""",
          (SELECT count(*) FROM violations v WHERE v.address_key = f.address_key
             AND v.violation_date <= f.first_date AND v.violation_date > f.first_date - INTERVAL 730 DAY)
            AS violations_2y, {permit_flags}""",
    )
    viol = cmodel["violation"]
    history = ", ".join(f"{k} {cmodel['trades'][k]['p'] * 100:.1f}%" for k in COMPLAINT_TRADES)
    leads = []
    for r in rows:
        lead = sr_lead(r, today, "complaint", "c", (14, 45))
        age = lead["ageDays"]
        open_trades = [k for k in COMPLAINT_TRADES if not r[f"done_{k}"]]
        if not open_trades:
            continue
        leads.append(
            lead
            | {
                "trades": open_trades,
                "trade": None,
                "title": "Building complaint filed, no citation yet",
                "probability": round(remaining_probability(viol["p"], viol["delays"], age), 4),
                "probabilityBasis": (
                    f"{viol['p'] * 100:.1f}% of 311 building complaints were followed by a city building violation at "
                    f"the same address within 120 days ({viol['episodes']:,} complaints, {cmodel['period']}); "
                    f"{adjusted(age)}. Same-trade permit within a year: {history} (also adjusted)."
                ),
                "tradeProbabilities": {
                    k: round(
                        remaining_probability(cmodel["trades"][k]["p"], cmodel["trades"][k]["delays"], age), 4
                    )
                    for k in open_trades
                },
                "evidence": [
                    {"label": "Complaint filed", "value": iso(r["first_date"])},
                    *requests_evidence(r, 60),
                    {"label": "311 status", "value": r["status"] or "—"},
                    {"label": "City violations in prior 2 years", "value": str(r["violations_2y"])},
                    *building_evidence(r),
                ],
                "action": owner_action(
                    r,
                    "Send a letter to the owner's mailing address now, before an inspector writes a citation; "
                    f"follow up at weeks 6, 12 and 24. When a citation follows, the median is {median_days(viol['delays'])} days after the complaint.",
                ),
            }
        )
    return leads


def porch_request_leads(con, today: date, pmodel: dict) -> list[dict]:
    rows = sr_rows(
        con,
        "Porch Inspection Request",
        today,
        120,
        "NOT EXISTS (SELECT 1 FROM p WHERE p.address_key = f.address_key AND p.t_porch AND p.issue_date > f.first_date)",
    )
    m = pmodel["porch"]
    leads = []
    for r in rows:
        lead = sr_lead(r, today, "porch_request", "pr", (14, 45))
        age = lead["ageDays"]
        leads.append(
            lead
            | {
                "trades": ["porch"],
                "trade": "porch",
                "title": "Porch inspection requested",
                "probability": round(remaining_probability(m["p"], m["delays"], age), 4),
                "probabilityBasis": (
                    f"{m['p'] * 100:.1f}% of 311 porch inspection requests were followed by a porch permit at the "
                    f"same address within a year ({m['episodes']:,} requests, {pmodel['period']}); "
                    f"{adjusted(age)}."
                ),
                "evidence": [
                    {"label": "Inspection requested", "value": iso(r["first_date"])},
                    *requests_evidence(r, 120),
                    {"label": "311 status", "value": r["status"] or "—"},
                    *building_evidence(r),
                ],
                "action": owner_action(
                    r,
                    "Send a letter to the owner's mailing address this week and offer a free porch assessment; "
                    "follow up at weeks 6, 12 and 24.",
                ),
            }
        )
    return leads


def vacant_leads(con, today: date, vmodel: dict) -> list[dict]:
    rows = sr_rows(
        con,
        "Vacant/Abandoned Building Complaint",
        today,
        180,
        "NOT EXISTS (SELECT 1 FROM sales s WHERE s.pin10 = f.k AND NOT s.filtered_out AND s.sale_date > f.first_date)",
        by_pin=True,
    )
    sale, trades = vmodel["sale"], vmodel["trades"]
    leads = []
    for r in rows:
        lead = sr_lead(r, today, "vacant", "vb", (30, 90))
        age = lead["ageDays"]
        leads.append(
            lead
            | {
                "trades": list(TRADES),
                "trade": None,
                "title": "Vacant building reported",
                "probability": round(remaining_probability(sale["p"], sale["delays"], age), 4),
                "probabilityBasis": (
                    f"{sale['p'] * 100:.1f}% of properties with a 311 vacant/abandoned-building complaint sold within "
                    f"a year ({sale['episodes']:,} complaints, {vmodel['period']}); "
                    f"{adjusted(age)}. Chance of work by trade is the share that pulled a permit of that type within two years "
                    f"({trades['general']['episodes']:,} complaints, {vmodel['permitPeriod']}); not adjusted for time passed."
                ),
                "tradeProbabilities": {k: round(trades[k]["p"], 4) for k in TRADES},
                "evidence": [
                    {"label": "Vacancy reported", "value": iso(r["first_date"])},
                    *requests_evidence(r, 180),
                    {"label": "311 status", "value": r["status"] or "—"},
                    *building_evidence(r),
                ],
                "action": owner_action(
                    r,
                    "Send a letter to the owner of record offering to secure, repair or renovate the building, or to "
                    "connect with a buyer; follow up at weeks 6, 12 and 24.",
                ),
            }
        )
    return leads


# ----------------------------------------------------------------------------------------------------------
# Closed restaurant spaces (signal lab H26)
# ----------------------------------------------------------------------------------------------------------
CLOSED_START = "2016-01-01"
CLOSED_LEAD_DAYS = 180


def lift_label(lift: float | None) -> str:
    """Plain-language strength of a lift, with the signal lab's verdict cut-offs (engine/score/signals.py)."""
    if lift is None:
        return "no comparison available"
    if lift < LIFT_WEAK:
        return "no real signal"
    return (
        "a weak signal" if lift < LIFT_USEFUL else "a useful lift" if lift < LIFT_STRONG else "a strong lift"
    )


def closed_restaurant_model(con) -> dict:
    """'Out of Business' restaurant inspections vs ordinary inspections (engine/score/food.py, signal lab H26).

    The period ends 365 days before the newest of the three sources involved, so every window is complete and
    the model moves forward as data arrives. Returns the three targets with sorted delays for time adjustment.
    """
    end = one(
        con,
        """
        SELECT least((SELECT max(inspection_date) FROM food_inspections),
                     (SELECT max(issue_date) FROM food_licenses),
                     (SELECT max(issue_date) FROM p)) - 365 AS d
    """,
    )["d"]
    views = closure_views(
        con, start=CLOSED_START, end=str(end), only=("license", "license_after30", "permit")
    )
    lic = views["license"]
    return {
        "start": CLOSED_START,
        "end": iso(end),
        "period": years([{"d": lic["first_signal"]}, {"d": lic["last_signal"]}]),
        "episodes": lic["signals"],
        "closuresPerWeek": lic["episodes_per_week"],
        **views,
    }


def closed_restaurant_leads(con, today: date, model: dict) -> list[dict]:
    """Restaurants recorded 'Out of Business' in the last 180 days, one lead per address.

    A closure starts an episode only if none was recorded at the address in the prior 365 days (the model's
    definition). Addresses where a retail food license under a different business name has already been issued
    after the closure are dropped: the space has found its next food tenant.
    """
    rows = q(
        con,
        f"""
        WITH recent AS (
          SELECT address_key AS k, inspection_date AS d, inspection_id, dba, license_no, lat, lon,
            {NAME_KEY.format(x="dba")} AS nm
          FROM food_inspections f
          WHERE facility_type = 'Restaurant' AND address_key IS NOT NULL AND {CLOSED}
            AND inspection_date > DATE '{today}' - INTERVAL {CLOSED_LEAD_DAYS} DAY
            AND NOT EXISTS (
              SELECT 1 FROM food_inspections h WHERE h.facility_type = 'Restaurant' AND h.address_key = f.address_key
                AND h.{CLOSED} AND h.inspection_date < f.inspection_date
                AND h.inspection_date >= f.inspection_date - INTERVAL 365 DAY)
          QUALIFY row_number() OVER (PARTITION BY address_key ORDER BY inspection_date, inspection_id) = 1
        ),
        e AS (
          SELECT * FROM recent r WHERE NOT EXISTS (
            SELECT 1 FROM (
              SELECT address_key AS k, issue_date AS d, {NAME_KEY.format(x="dba")} AS nm FROM food_licenses
              WHERE address_key IS NOT NULL AND issue_date IS NOT NULL
            ) t WHERE t.k = r.k AND t.d > r.d AND NOT {SAME_NAME.replace("e.nm", "r.nm")}
          )
        )
        SELECT e.*, par.address, par.owner_name, par.owner_mailing, par.units, rc.year_built, rc.ext_wall,
          coalesce(ca.community_area, aa.community_area, pa.community_area, za.community_area) AS community_area,
          coalesce({COMPANY_SQL.format(col="par.owner_name")}, false) AS company,
          (SELECT min(inspection_date) FROM food_inspections x WHERE x.address_key = e.k) AS first_inspection,
          (SELECT count(DISTINCT coalesce(l.account_number::VARCHAR, {NAME_KEY.format(x="l.dba")}))
             FROM food_licenses l WHERE l.address_key = e.k AND l.issue_date >= DATE '{CLOSED_START}') AS businesses,
          (SELECT count(*) FROM p WHERE p.address_key = e.k AND {RENO_PREDICATE}
             AND p.issue_date <= e.d AND p.issue_date > e.d - INTERVAL 730 DAY) AS reno_2y,
          (SELECT count(*) FROM p WHERE p.address_key = e.k AND {RENO_PREDICATE} AND p.issue_date > e.d) AS reno_since
        FROM e
        LEFT JOIN addr_parcel ap ON ap.address_key = e.k
        LEFT JOIN parcels par ON par.pin10 = ap.pin10
        LEFT JOIN res_chars rc ON rc.pin10 = ap.pin10
        LEFT JOIN ca_geom ca ON e.lat IS NOT NULL AND ST_Contains(ca.geom, ST_Point(e.lon, e.lat))
        LEFT JOIN addr_area aa ON aa.address_key = e.k
        LEFT JOIN pin_area pa ON pa.pin10 = ap.pin10
        LEFT JOIN zip_area za ON za.zip = par.zip
        QUALIFY row_number() OVER (PARTITION BY e.inspection_id ORDER BY ca.community_area NULLS LAST) = 1
        ORDER BY e.d DESC, e.inspection_id
    """,
    )
    lic, late, permit = model["license"], model["license_after30"], model["permit"]
    spread = f"{late['days_p25']:.0f}–{late['days_p75']:.0f}"
    leads = []
    for r in rows:
        age = (today - r["d"]).days
        owner_type = "company" if r["company"] else "individual"
        evidence = [
            {"label": "Restaurant", "value": title(r["dba"]) or "—"},
            {"label": "License number", "value": str(r["license_no"]) if r["license_no"] else "—"},
            {"label": "Closure recorded", "value": iso(r["d"])},
            {"label": "First food inspection on record", "value": iso(r["first_inspection"])},
            {
                "label": f"Food businesses licensed here since {CLOSED_START[:4]}",
                "value": str(r["businesses"]),
            },
            {"label": "Renovation permits in the 2 years before", "value": str(r["reno_2y"])},
        ]
        if r["reno_since"]:
            evidence.append({"label": "Renovation permits since the closure", "value": str(r["reno_since"])})
        leads.append(
            {
                "id": f"cr-{r['inspection_id']}",
                "kind": "closed_restaurant",
                "trades": ["general"],
                "trade": "general",
                "title": "Restaurant space closed",
                "address": title(r["address"] or r["k"]),
                "communityArea": r["community_area"],
                "signalDate": iso(r["d"]),
                "ageDays": age,
                "tier": "act_now" if age <= 30 else "this_week" if age <= 90 else "monitor",
                "owner": {
                    "name": title(r["owner_name"]),
                    "type": owner_type,
                    "mailing": title(r["owner_mailing"]),
                    "units": r["units"],
                },
                "probability": round(remaining_probability(lic["conversion"], lic["delays"], age), 4),
                "probabilityBasis": (
                    f"{lic['conversion'] * 100:.1f}% of {lic['signals']:,} restaurant closures ({model['period']}) were "
                    f"followed by a new food business license under a different name at the same address within a year, "
                    f"vs {lic['baseline'] * 100:.1f}% after ordinary inspections ({lic['lift']:.1f}x). Counting only "
                    f"licenses issued 31+ days after the closure: {late['conversion'] * 100:.1f}% vs "
                    f"{late['baseline'] * 100:.1f}% ({late['lift']:.1f}x), median {late['median_days']:.0f} days, middle "
                    f"half {spread} days; {adjusted(age)}. Renovation, build-out or new-construction permit within a "
                    f"year: {permit['conversion'] * 100:.1f}% vs {permit['baseline'] * 100:.1f}% "
                    f"({permit['lift']:.2f}x, {lift_label(permit['lift'])}), also adjusted."
                ),
                "tradeProbabilities": {
                    "general": round(remaining_probability(permit["conversion"], permit["delays"], age), 4)
                },
                "evidence": [*evidence, *building_evidence(r)],
                "action": owner_action(
                    r,
                    "Send a letter to the property owner's mailing address offering to prepare or build out the "
                    "space for the next tenant; follow up at weeks 6, 12 and 24.",
                )
                + f" Most later food licenses arrive {spread} days after the closure (middle half of licenses issued 31+ days later).",
                "sourceUrl": f"https://data.cityofchicago.org/resource/4ijn-s7e5.json?inspection_id={r['inspection_id']}",
                "restaurant": {
                    "name": title(r["dba"]),
                    "licenseNo": r["license_no"] if r["license_no"] else None,
                },
                "_addressKey": r["k"],
            }
        )
    return leads


# ----------------------------------------------------------------------------------------------------------
# Commercial pilot material: new business coming (H33) and trades still open after a big permit (H29)
# ----------------------------------------------------------------------------------------------------------
NB_LEAD_DAYS = 180
NB_ROWS = 400
BIG_RECENT_DAYS = 365
BIG_ROWS = 300
MOSTLY_LOCKED_BELOW = (
    0.6  # a trade is 'mostly locked in' when under this share of its follow-on permits go to a new contractor
)
NON_CONTRACTOR_ROLES = {"owner", "owner_gc", "architect", "engineer", "expediter", "other"}
ROLE_LABELS = {
    "gc": "General contractor",
    "electrical": "Electrical",
    "plumbing": "Plumbing",
    "hvac": "HVAC",
    "masonry": "Masonry",
    "sign": "Signs",
    "elevator": "Elevator",
    "wrecking": "Demolition",
}


def trim_text(s: str | None, limit: int = 160) -> str:
    s = re.sub(r"\s+", " ", (s or "").strip())
    if len(s) <= limit:
        return s
    return s[:limit].rsplit(" ", 1)[0].rstrip(",;:- ") + "…"


def permit_parties_by(con, sql: str, keys: list[str]) -> dict[str, dict]:
    """Contractors (the lab's `ctr` rule) and the applicant named on permits. `sql` selects key, role, role_raw,
    name_raw, name_key, slot for the keys passed as the single list parameter."""
    out: dict[str, dict] = {k: {"contractors": {}, "applicant": None} for k in keys}
    cur = con.execute(sql, [keys])
    rows = sorted(cur.fetchall(), key=lambda r: (r[0], r[5] or 0, r[4] or "", r[3] or ""))
    for key, role, role_raw, name_raw, name_key, _slot in rows:
        entry = out[key]
        if not name_key:
            continue
        raw = role_raw or ""
        if (role is not None and role not in NON_CONTRACTOR_ROLES) or "CONTRACTOR" in raw:
            entry["contractors"].setdefault(
                name_key,
                {"name": title(name_raw), "role": ROLE_LABELS.get(role or "", title(raw) or "Contractor")},
            )
        elif role == "other" and "APPLICANT" in raw and entry["applicant"] is None:
            entry["applicant"] = title(name_raw)
    for entry in out.values():
        found = sorted(
            entry["contractors"].items(), key=lambda kv: (kv[1]["role"] != "General contractor", kv[0])
        )
        entry["contractors"] = [v for _, v in found][:4]
    return out


def permit_places(con, pids: list[str]) -> dict[str, dict]:
    """Per permit id: permit type and text, plus the address, owner of record and community area, with the same
    fallbacks the leads use (point in polygon, address, parcel, ZIP)."""
    cur = con.execute(
        f"""
        SELECT pm.id AS pid, pm.permit_type, pm.description, pm.address_key AS k,
          par.address, par.owner_name, par.owner_mailing, par.units,
          coalesce({COMPANY_SQL.format(col="par.owner_name")}, false) AS company,
          coalesce(ca.community_area, aa.community_area, pa.community_area, za.community_area) AS community_area
        FROM p pm
        LEFT JOIN addr_parcel ap ON ap.address_key = pm.address_key
        LEFT JOIN parcels par ON par.pin10 = ap.pin10
        LEFT JOIN ca_geom ca ON pm.lat IS NOT NULL AND ST_Contains(ca.geom, ST_Point(pm.lon, pm.lat))
        LEFT JOIN addr_area aa ON aa.address_key = pm.address_key
        LEFT JOIN pin_area pa ON pa.pin10 = ap.pin10
        LEFT JOIN zip_area za ON za.zip = par.zip
        WHERE pm.id IN (SELECT unnest(?::VARCHAR[]))
        QUALIFY row_number() OVER (
          PARTITION BY pm.id ORDER BY ca.community_area NULLS LAST, par.pin10, par.owner_name, par.address) = 1
        """,
        [pids],
    )
    cols = [d[0] for d in cur.description]
    return {r["pid"]: r for r in (dict(zip(cols, row, strict=True)) for row in cur.fetchall())}


def new_business_model(con) -> dict:
    """H33 (engine/score/licenses.py): build-out permit at an unlicensed commercial, mixed-use or 7+ unit address ->
    a new business license there within 365 days. The period ends 365 days before the newest license record so
    every window is complete, so it moves forward as data arrives."""
    newest = one(con, "SELECT max(issue_date) AS d FROM biz_license_history")["d"]
    end = newest - timedelta(days=365)
    m = licenses.new_business(con, end=end.isoformat())
    m["period"] = years([{"d": m["first_signal"]}, {"d": m["last_signal"]}])
    return m


def new_business_summary(m: dict) -> dict:
    return {
        "period": m["period"],
        "signals": m["signals"],
        "rate": round(m["conversion"], 4),
        "matchedRate": round(m["baseline"], 4),
        "lift": round(m["lift"], 4),
        "busyRate": round(m["busy_control_rate"], 4),
        "liftVsBusy": round(m["lift_vs_busy_control"], 4),
        "medianDays": round(m["median_days"], 1),
        "daysP25": round(m["days_p25"], 1),
        "daysP75": round(m["days_p75"], 1),
        "perWeek": round(m["signals_per_week"], 2),
        "byClass": [
            {
                "class": r["class"],
                "signals": r["signals"],
                "rate": round(r["new_license_rate"], 4),
                "matchedRate": round(r["control_rate"], 4),
                "lift": round(r["lift"], 4),
            }
            for r in m["by_class"]
        ],
        "byGroup": [
            {"group": r["license_group"], "share": round(r["share_of_conversions"], 4)} for r in m["by_group"]
        ],
    }


def new_business_spaces(con, today: date, model: dict, closed_keys: set[str]) -> tuple[list[dict], int]:
    """Build-out permits issued in the last 180 days (as of the newest permit) at addresses with no business license
    in force on the permit date (the H33 signal) and none issued since. Newest first, capped at NB_ROWS."""
    licenses.build_out_current(con, asof=today, days=NB_LEAD_DAYS)
    base = q(con, "SELECT k, d, bucket, cost, pid FROM lc_cur ORDER BY d DESC, pid")
    total = len(base)
    base = base[:NB_ROWS]
    pids = [r["pid"] for r in base]
    places = permit_places(con, pids)
    parties = permit_parties_by(
        con,
        "SELECT permit_id, role, role_raw, name_raw, name_key, slot FROM permit_parties "
        "WHERE permit_id IN (SELECT unnest(?::VARCHAR[]))",
        pids,
    )
    class_rate = {c["class"]: c["new_license_rate"] for c in model["by_class"]}
    spaces = []
    for r in base:
        pl = places[r["pid"]]
        age = (today - r["d"]).days
        crate = class_rate[r["bucket"]]
        company = bool(pl["company"])
        spaces.append(
            {
                "id": f"nb-{r['pid']}",
                "address": title(pl["address"] or r["k"]),
                "communityArea": pl["community_area"],
                "class": r["bucket"],
                "permitDate": iso(r["d"]),
                "ageDays": age,
                "reportedCost": r["cost"] or None,
                "workDescription": trim_text(pl["description"]),
                "contractors": parties[r["pid"]]["contractors"],
                "applicant": parties[r["pid"]]["applicant"],
                "owner": {
                    "name": title(pl["owner_name"]),
                    "company": company,
                    "mailing": title(pl["owner_mailing"]),
                },
                "alsoClosedRestaurant": r["k"] in closed_keys,
                "classRate": round(crate, 4),
                "historicalRate": round(remaining_probability(crate, model["delays"], age), 4),
                "sourceUrl": f"https://data.cityofchicago.org/resource/ydr8-5enu.json?id={r['pid']}",
            }
        )
    return spaces, total


def open_trades_model(con) -> dict:
    """H29 (engine/score/licenses.py): $1M+ permit -> follow-on permits by trade within 540 days and who gets them.
    The period ends 540 days before the newest permit so every window is complete."""
    m = licenses.open_trades(con)
    first = one(
        con,
        f"SELECT min(d) AS d FROM lc_sig WHERE d <= DATE '{m['period_end']}' AND bucket IN ({licenses.BUCKET_LIST_29})",
    )["d"]
    m["period"] = years([{"d": first}, {"d": m["period_end"]}])
    return m


def open_trades_summary(m: dict) -> dict:
    def r4(x):
        return None if x is None else round(x, 4)

    rows = [
        {
            "trade": t["trade"],
            "label": licenses.TRADE_LABELS[t["trade"]],
            "signals": t["signals"],
            "followOnRate": r4(t["followon_rate"]),
            "newContractorRate": r4(t["new_contractor_rate"]),
            "newShare": r4(t["new_share"]),
            "lockedShare": r4(t["locked_share"]),
            "unnamedShare": r4(t["unnamed_share"]),
            "liftVsBusy": r4(t["lift_vs_busy"]),
            "medianDays": None if t["median_days"] is None else round(t["median_days"], 1),
            "daysP25": None if t["p25_days"] is None else round(t["p25_days"], 1),
            "daysP75": None if t["p75_days"] is None else round(t["p75_days"], 1),
            "mostlyLockedIn": t["new_share"] is None or t["new_share"] < MOSTLY_LOCKED_BELOW,
        }
        for t in m["by_trade"]
    ]
    rows.sort(key=lambda t: (-(t["newContractorRate"] or 0), t["trade"]))
    return {
        "period": m["period"],
        "bigPermits": m["signals"],
        "perWeek": round(m["signals_per_week"], 2),
        "perWeekClassKnown": round(m["signals_per_week_class_known"], 2),
        "medianDays": round(m["median_days"], 1),
        "daysP25": round(m["days_p25"], 1),
        "daysP75": round(m["days_p75"], 1),
        "headlineTrades": list(licenses.HEADLINE_TRADES),
        "followOnRate": round(m["conversion"], 4),
        "liftVsBusy": round(m["lift_vs_busy"], 4),
        "byTrade": rows,
    }


def open_trades_recent(con, today: date) -> tuple[list[dict], int]:
    """$1M+ new-construction or renovation permits in the last 365 days, newest first (capped at BIG_ROWS), with the
    follow-on trades that have already appeared at the address since."""
    base = licenses.recent_big_permits(con, asof=today.isoformat(), days=BIG_RECENT_DAYS)
    total = len(base)
    base = base[:BIG_ROWS]
    places = permit_places(con, [r["pid"] for r in base])
    parties = permit_parties_by(
        con,
        "SELECT m.sk, pp.role, pp.role_raw, pp.name_raw, pp.name_key, pp.slot FROM lc_maj_all m "
        "JOIN permit_parties pp ON pp.permit_id = m.id WHERE m.sk IN (SELECT unnest(?::VARCHAR[]))",
        [r["sk"] for r in base],
    )
    out = []
    for r in base:
        pl = places[r["pid"]]
        out.append(
            {
                "id": f"bp-{r['pid']}",
                "address": title(pl["address"] or r["k"]),
                "communityArea": pl["community_area"],
                "class": r["bucket"],
                "permitType": "New construction"
                if pl["permit_type"] == "PERMIT - NEW CONSTRUCTION"
                else "Renovation/alteration",
                "permitDate": iso(r["d"]),
                "ageDays": (today - r["d"]).days,
                "reportedCost": r["cost"],
                "description": trim_text(pl["description"]),
                "contractors": parties[r["sk"]]["contractors"],
                "appeared": r["appeared"],
                "sourceUrl": f"https://data.cityofchicago.org/resource/ydr8-5enu.json?id={r['pid']}",
            }
        )
    return out, total


# ----------------------------------------------------------------------------------------------------------
# Block targeting (signal lab H03)
# ----------------------------------------------------------------------------------------------------------
def roofing_blocks(con, today: date) -> dict:
    """Blocks (~160 m cells) with 2+ reroof permits in the last 90 days, plus the historical neighbor lift."""
    rows = q(
        con,
        """
        WITH snap AS (SELECT unnest(generate_series(DATE '2016-01-01', DATE '2025-01-01', INTERVAL 3 MONTH))::DATE AS d),
        rr AS (SELECT pin10, issue_date FROM p WHERE t_roofing AND pin10 IS NOT NULL),
        cell_prior AS (
          SELECT s.d, r.cy, r.cx, count(DISTINCT rr.pin10) AS n
          FROM snap s JOIN rr ON rr.issue_date > s.d - INTERVAL 90 DAY AND rr.issue_date <= s.d
          JOIN resi r ON r.pin10 = rr.pin10 GROUP BY ALL
        ),
        u AS (
          SELECT r.pin10, coalesce(c.n, 0) AS n,
            EXISTS (SELECT 1 FROM rr x WHERE x.pin10 = r.pin10 AND x.issue_date > s.d - INTERVAL 90 DAY
                    AND x.issue_date <= s.d) AS self_recent,
            EXISTS (SELECT 1 FROM rr x WHERE x.pin10 = r.pin10 AND x.issue_date > s.d
                    AND x.issue_date <= s.d + INTERVAL 180 DAY) AS y
          FROM snap s CROSS JOIN resi r LEFT JOIN cell_prior c ON c.d = s.d AND c.cy = r.cy AND c.cx = r.cx
        )
        SELECT CASE WHEN n = 0 THEN 'base' WHEN n >= 2 THEN 'exposed' END AS grp, count(*) AS cases, avg(y::INT) AS rate
        FROM u WHERE NOT self_recent AND n <> 1 GROUP BY 1
    """,
    )
    g = {r["grp"]: r for r in rows}
    model = {
        "exposedRate": round(g["exposed"]["rate"], 4),
        "baseRate": round(g["base"]["rate"], 4),
        "lift": round(g["exposed"]["rate"] / g["base"]["rate"], 2),
        "exposedCases": g["exposed"]["cases"],
        "baseCases": g["base"]["cases"],
        "horizonDays": 180,
        "period": "2016–2025",
    }
    cells = q(
        con,
        f"""
        WITH parcel_addr AS (
          SELECT pin10, min(regexp_replace(trim(address), '\\s+', ' ', 'g')) AS address FROM parcels
          WHERE regexp_matches(upper(regexp_replace(trim(address), '\\s+', ' ', 'g')), '{COMPLETE_ADDRESS}')
          GROUP BY 1
        ),
        rr AS (
          SELECT r.cy, r.cx, r.pin10, max(p.issue_date) AS last_date,
                 coalesce(pa.address,
                   first(p.address_key ORDER BY p.issue_date DESC, p.id)
                     FILTER (WHERE regexp_matches(p.address_key, '{COMPLETE_ADDRESS}'))) AS address
          FROM p JOIN resi r USING (pin10) LEFT JOIN parcel_addr pa ON pa.pin10 = r.pin10
          WHERE p.t_roofing AND p.issue_date > DATE '{today}' - INTERVAL 90 DAY
          GROUP BY r.cy, r.cx, r.pin10, pa.address
        ),
        top AS (
          SELECT cy, cx, count(*) AS recent, max(last_date) AS last_date,
                 list(address ORDER BY last_date DESC, pin10) FILTER (WHERE address IS NOT NULL) AS addresses,
                 list(pin10) AS pins
          FROM rr GROUP BY cy, cx HAVING count(*) >= 2 ORDER BY recent DESC, cy, cx LIMIT 100
        )
        SELECT t.cy, t.cx, t.recent, t.last_date, t.addresses,
          (SELECT count(*) FROM resi r WHERE r.cy = t.cy AND r.cx = t.cx) AS parcels,
          (SELECT first(community_area ORDER BY n DESC, community_area) FROM (
             SELECT pa.community_area, count(*) AS n FROM pin_area pa WHERE list_contains(t.pins, pa.pin10)
             GROUP BY 1)) AS community_area
        FROM top t ORDER BY t.recent DESC, t.cy, t.cx
    """,
    )
    blocks = [
        {
            "id": f"{c['cy']}:{c['cx']}",
            "communityArea": c["community_area"],
            "recentReroofs": c["recent"],
            "lastPermit": iso(c["last_date"]),
            "residentialParcels": c["parcels"],
            "addresses": [title(a) for a in (c["addresses"] or [])[:5]],
        }
        for c in cells
    ]
    return {"roofing": blocks, "roofingModel": model}


def preapp_projects(con, today: date) -> dict:
    build_parcel_features(
        con,
        f"""
        SELECT unnest(generate_series(DATE '2019-01-01', DATE '2025-07-01', INTERVAL 6 MONTH))::DATE AS d
        UNION ALL SELECT DATE '{today}'
        """,
    )
    base = fit_combo_rates(con, "d BETWEEN DATE '2019-01-01' AND DATE '2025-07-01'")
    cols = ", ".join(PARCEL_FEATURES)
    rows = q(
        con,
        f"""
        WITH scored AS (
          SELECT f.*, c.rate, c.n FROM feat f JOIN combo c USING ({cols}) WHERE f.d = DATE '{today}'
        ),
        top AS (SELECT * FROM scored ORDER BY rate DESC, hash(pin10), pin10 LIMIT 150)
        SELECT t.*, par.address, par.owner_name, pa.community_area,
          (SELECT list({{'date': p.issue_date, 'type': p.permit_type, 'cost': p.reported_cost,
                         'description': left(p.description, 140)}} ORDER BY p.issue_date DESC, p.id)[:3]
             FROM p WHERE p.pin10 = t.pin10) AS recent_permits,
          (SELECT list(DISTINCT pp.name_raw ORDER BY pp.name_raw)[:3] FROM p JOIN permit_parties pp ON pp.permit_id = p.id
             WHERE p.pin10 = t.pin10 AND pp.role = 'gc' AND p.issue_date > DATE '{today}' - INTERVAL 1095 DAY)
            AS recent_gcs
        FROM top t LEFT JOIN parcels par USING (pin10) LEFT JOIN pin_area pa USING (pin10)
        ORDER BY t.rate DESC, hash(t.pin10), t.pin10
    """,
    )
    projects = []
    for r in rows:
        projects.append(
            {
                "id": f"pa-{r['pin10']}",
                "address": title(r["address"]) or f"PIN {r['pin10']}",
                "communityArea": r["community_area"],
                "owner": title(r["owner_name"]),
                "probability": round(r["rate"], 4),
                "lift": round(r["rate"] / base, 1),
                "historicalCases": r["n"],
                "signals": [label for f, label in PARCEL_FEATURES.items() if r[f]],
                "recentPermits": [
                    {
                        "date": iso(x["date"]),
                        "type": title(x["type"].replace("PERMIT - ", "")),
                        "cost": x["cost"],
                        "description": (x["description"] or "").capitalize(),
                    }
                    for x in (r["recent_permits"] or [])
                ],
                "recentGcs": [title(x) for x in (r["recent_gcs"] or [])],
            }
        )
    return {"baseRate": base, "projects": projects}


def gc_targets(con, today: date) -> dict:
    out = {}
    for trade in COMMERCIAL_SUB_TRADES:
        rows = q(
            con,
            f"""
            WITH jobs AS (
              SELECT m.id, m.issue_date, m.reported_cost, m.community_area, gc.gc, gc.gc_name, sub.sub, sub.sub_name
              FROM (SELECT id, issue_date, reported_cost, community_area FROM p WHERE {MAJOR}) m
              JOIN (SELECT permit_id, min(name_key) AS gc, min(name_raw) AS gc_name FROM permit_parties
                    WHERE role = 'gc' AND name_key <> '' GROUP BY 1) gc ON gc.permit_id = m.id
              JOIN (SELECT permit_id, min(name_key) AS sub, min(name_raw) AS sub_name FROM permit_parties
                    WHERE role = '{trade}' AND name_key <> '' GROUP BY 1) sub ON sub.permit_id = m.id
            ),
            j AS (
              SELECT jobs.*,
                     row_number() OVER (PARTITION BY gc, sub ORDER BY issue_date, id) = 1 AS is_new,
                     row_number() OVER (PARTITION BY gc ORDER BY issue_date, id) AS k
              FROM jobs
            ),
            g AS (
              SELECT gc, first(gc_name ORDER BY issue_date DESC, id) AS gc_name, count(*) AS jobs_total,
                avg(is_new::INT) FILTER (WHERE k > 1) AS open_door,
                -- shrink toward the ~15% citywide new-sub rate so GCs with few jobs don't top the list
                (sum(is_new::INT) FILTER (WHERE k > 1) + 0.75) / (count(*) FILTER (WHERE k > 1) + 5)
                  AS open_door_smoothed,
                count(*) FILTER (WHERE issue_date > DATE '{today}' - INTERVAL 730 DAY) AS jobs_24m,
                median(reported_cost) FILTER (WHERE issue_date > DATE '{today}' - INTERVAL 730 DAY) AS median_cost,
                max(issue_date) AS last_job
              FROM j GROUP BY gc
            )
            SELECT g.*,
              (SELECT list({{'name': sub_name, 'jobs': n}} ORDER BY n DESC, sub)[:3] FROM (
                 SELECT sub, first(sub_name ORDER BY issue_date DESC, id) AS sub_name, count(*) AS n FROM jobs
                 WHERE jobs.gc = g.gc AND issue_date > DATE '{today}' - INTERVAL 730 DAY GROUP BY sub)) AS subs,
              (SELECT list(community_area ORDER BY n DESC, community_area)[:3] FROM (
                 SELECT community_area, count(*) AS n FROM jobs
                 WHERE jobs.gc = g.gc AND issue_date > DATE '{today}' - INTERVAL 730 DAY
                   AND community_area IS NOT NULL GROUP BY 1)) AS areas
            FROM g WHERE jobs_total >= 6 AND jobs_24m >= 2
            ORDER BY open_door_smoothed * ln(1 + jobs_24m) DESC, gc LIMIT 60
        """,
        )
        out[trade] = [
            {
                "gc": title(r["gc_name"]),
                "openDoor": round(r["open_door"] or 0, 3),
                "jobsTotal": r["jobs_total"],
                "jobs24m": r["jobs_24m"],
                "medianCost": r["median_cost"],
                "lastJob": iso(r["last_job"]),
                "currentSubs": [{"name": title(s["name"]), "jobs": s["jobs"]} for s in (r["subs"] or [])],
                "areas": r["areas"] or [],
            }
            for r in rows
        ]
    return out


def competitors(con, today: date, won: list[dict]) -> dict:
    out = {}
    for k, t in TRADES.items():
        rows = q(
            con,
            f"""
            WITH x AS (
              SELECT p.id, p.issue_date, p.reported_cost, p.community_area, pp.name_key, pp.name_raw
              FROM p JOIN permit_parties pp ON pp.permit_id = p.id AND pp.role = '{t["role"]}'
              WHERE p.t_{t["permit"]} AND pp.name_key <> '' AND p.issue_date > DATE '{today}' - INTERVAL 730 DAY
            ),
            c AS (
              SELECT name_key, first(name_raw ORDER BY issue_date DESC, id, name_raw) AS name,
                count(DISTINCT id) FILTER (WHERE issue_date > DATE '{today}' - INTERVAL 365 DAY) AS jobs_12m,
                count(DISTINCT id) FILTER (WHERE issue_date <= DATE '{today}' - INTERVAL 365 DAY) AS jobs_prev,
                median(reported_cost) FILTER (WHERE reported_cost > 0) AS median_cost
              FROM x GROUP BY 1
            )
            SELECT c.*, c.jobs_12m / sum(c.jobs_12m) OVER () AS share,
              (SELECT list(community_area ORDER BY n DESC, community_area)[:3] FROM (
                 SELECT community_area, count(*) AS n FROM x WHERE x.name_key = c.name_key
                   AND community_area IS NOT NULL GROUP BY 1)) AS areas
            FROM c WHERE jobs_12m > 0 ORDER BY jobs_12m DESC, name_key LIMIT 25
        """,
        )
        won_counts: dict[str, int] = {}
        for w in won:
            if w["trade"] == k and w["contractor"]:
                won_counts[w["contractor"]] = won_counts.get(w["contractor"], 0) + 1
        out[k] = {
            "contractors": [
                {
                    "name": title(r["name"]),
                    "jobs12m": r["jobs_12m"],
                    "jobsPrev12m": r["jobs_prev"],
                    "share": round(r["share"], 4),
                    "medianCost": r["median_cost"],
                    "areas": r["areas"] or [],
                }
                for r in rows
            ],
            "violationJobsWon": sorted(
                ({"name": n, "jobs": c} for n, c in won_counts.items()), key=lambda x: (-x["jobs"], x["name"])
            )[:10],
        }
    return out


def areas(con, today: date, today_sales: date) -> list[dict]:
    vt = [t["violation"] for t in TRADES.values() if t["violation"]]
    v_cols = ", ".join(
        f"count(*) FILTER (WHERE t_{t} AND violation_date > DATE '{today}' - INTERVAL 90 DAY) AS v_{t}, "
        f"count(*) FILTER (WHERE t_{t} AND violation_date BETWEEN DATE '{today}' - INTERVAL 455 DAY "
        f"AND DATE '{today}' - INTERVAL 365 DAY) AS v_{t}_ly"
        for t in vt
    )
    p_cols = ", ".join(
        f"count(*) FILTER (WHERE t_{t['permit']} AND issue_date > DATE '{today}' - INTERVAL 90 DAY) AS p_{k}, "
        f"count(*) FILTER (WHERE t_{t['permit']} AND issue_date BETWEEN DATE '{today}' - INTERVAL 455 DAY "
        f"AND DATE '{today}' - INTERVAL 365 DAY) AS p_{k}_ly"
        for k, t in TRADES.items()
    )
    rows = q(
        con,
        f"""
        WITH v AS (
          SELECT aa.community_area, {v_cols} FROM violations JOIN addr_area aa USING (address_key)
          WHERE violation_date > DATE '{today}' - INTERVAL 455 DAY GROUP BY 1
        ),
        pm AS (
          SELECT community_area, {p_cols},
            count(*) FILTER (WHERE {MAJOR} AND issue_date > DATE '{today}' - INTERVAL 90 DAY) AS major,
            sum(reported_cost) FILTER (WHERE {MAJOR} AND issue_date > DATE '{today}' - INTERVAL 90 DAY) AS major_value,
            count(*) FILTER (WHERE {MAJOR} AND issue_date BETWEEN DATE '{today}' - INTERVAL 455 DAY
                             AND DATE '{today}' - INTERVAL 365 DAY) AS major_ly
          FROM p WHERE community_area IS NOT NULL AND issue_date > DATE '{today}' - INTERVAL 455 DAY GROUP BY 1
        ),
        s AS (
          SELECT pa.community_area,
            count(*) FILTER (WHERE sales.sale_date > DATE '{today_sales}' - INTERVAL 180 DAY) AS inv,
            count(*) FILTER (WHERE sales.sale_date BETWEEN DATE '{today_sales}' - INTERVAL 545 DAY
                             AND DATE '{today_sales}' - INTERVAL 365 DAY) AS inv_ly,
            median(sale_price) FILTER (WHERE sales.sale_date > DATE '{today_sales}' - INTERVAL 180 DAY) AS price
          FROM sales JOIN pin_area pa USING (pin10)
          WHERE NOT filtered_out AND {COMPANY_SQL.format(col="buyer_name")}
            AND NOT regexp_matches(upper(coalesce(buyer_name, '')), '{NON_OPERATOR_RE}')
          GROUP BY 1
        )
        SELECT ca.community_area, ca.name, v.*, pm.*, s.inv, s.inv_ly, s.price
        FROM community_areas ca
        LEFT JOIN v USING (community_area) LEFT JOIN pm USING (community_area) LEFT JOIN s USING (community_area)
        ORDER BY ca.community_area
    """,
    )
    out = []
    for r in rows:
        out.append(
            {
                "id": r["community_area"],
                "name": r["name"],
                "violations": {
                    k: {
                        "last90": r.get(f"v_{t['violation']}") or 0,
                        "lastYear": r.get(f"v_{t['violation']}_ly") or 0,
                    }
                    for k, t in TRADES.items()
                    if t["violation"]
                },
                "permits": {
                    k: {"last90": r.get(f"p_{k}") or 0, "lastYear": r.get(f"p_{k}_ly") or 0} for k in TRADES
                },
                "majorProjects": {
                    "last90": r["major"] or 0,
                    "lastYear": r["major_ly"] or 0,
                    "value90": r["major_value"] or 0,
                },
                "investorPurchases": {"last180": r["inv"] or 0, "lastYear": r["inv_ly"] or 0},
                "medianInvestorPrice": r["price"],
            }
        )
    return out


# ----------------------------------------------------------------------------------------------------------
def build(out: Path) -> dict:
    con = db.connect(memory_limit="8GB")
    today = prepare(con)
    dates = as_of(con)
    print("models ...", flush=True)
    vmodel = violation_model(con)
    smodel = sale_model(con)
    values = job_values(con, today)
    print("violation leads ...", flush=True)
    v_leads, won = violation_leads(con, dates["violations"], vmodel, values)
    print("investor leads ...", flush=True)
    s_leads = investor_leads(con, today, dates["sales"], smodel)
    print("311 leads ...", flush=True)
    cmodel, pmodel, xmodel = complaint_model(con), porch_request_model(con), vacant_model(con)
    c_leads = complaint_leads(con, dates["complaints"], cmodel)
    pr_leads = porch_request_leads(con, dates["complaints"], pmodel)
    vb_leads = vacant_leads(con, dates["complaints"], xmodel)
    print("closed restaurant leads ...", flush=True)
    rmodel = closed_restaurant_model(con)
    cr_leads = closed_restaurant_leads(con, dates["foodInspections"], rmodel)
    closed_keys = {lead.pop("_addressKey") for lead in cr_leads}
    print("new business spaces (H33) and open trades (H29) ...", flush=True)
    nbmodel = new_business_model(con)
    nb_spaces, nb_total = new_business_spaces(con, today, nbmodel, closed_keys)
    otmodel = open_trades_model(con)
    ot_recent, ot_total = open_trades_recent(con, today)
    print("roofing blocks ...", flush=True)
    blocks = roofing_blocks(con, today)
    print("pre-application projects ...", flush=True)
    pre = preapp_projects(con, today)
    print("gc targets, competitors, areas ...", flush=True)
    snapshot = {
        "meta": {
            "generatedAt": generated_at(dates),
            "dataAsOf": {k: iso(v) for k, v in dates.items()},
            "sources": [
                {
                    "name": "City of Chicago building permits",
                    "url": "https://data.cityofchicago.org/d/ydr8-5enu",
                },
                {
                    "name": "City of Chicago building violations",
                    "url": "https://data.cityofchicago.org/d/22u3-xenr",
                },
                {
                    "name": "Cook County Assessor parcel sales",
                    "url": "https://datacatalog.cookcountyil.gov/d/wvhk-k5uv",
                },
                {
                    "name": "Cook County Assessor parcel addresses",
                    "url": "https://datacatalog.cookcountyil.gov/d/3723-97qp",
                },
                {
                    "name": "Cook County Assessor residential characteristics",
                    "url": "https://datacatalog.cookcountyil.gov/d/x54s-btds",
                },
                {
                    "name": "City of Chicago 311 service requests",
                    "url": "https://data.cityofchicago.org/d/v6vf-nfxy",
                },
                {
                    "name": "City of Chicago food inspections",
                    "url": "https://data.cityofchicago.org/d/4ijn-s7e5",
                },
                {
                    "name": "City of Chicago business licenses (retail food establishments)",
                    "url": "https://data.cityofchicago.org/d/r5kz-chrr",
                },
            ],
            "assumptions": {"winRate": WIN_RATE, "margin": MARGIN},
        },
        "trades": {k: {"label": t["label"], "jobValue": values[k]} for k, t in TRADES.items()},
        "models": {
            "violation": {
                k: {
                    o: {"episodes": m["episodes"], "p365": round(m["p"], 4)}
                    for o, m in v.items()
                    if o in OWNERS
                }
                for k, v in vmodel.items()
            },
            "investorPurchase": {
                seg: {
                    "purchases": m["purchases"],
                    "pAny": round(m["p_any"], 4),
                    "pMajor": round(m["p_major"], 4),
                    "pTrade": {k: round(x, 4) for k, x in m["p_trade"].items()},
                }
                for seg, m in smodel.items()
            },
            "complaint": {
                "period": cmodel["period"],
                "episodes": cmodel["violation"]["episodes"],
                "pViolation120": round(cmodel["violation"]["p"], 4),
                "medianDaysToViolation": median_days(cmodel["violation"]["delays"]),
                "pTrade365": {k: round(m["p"], 4) for k, m in cmodel["trades"].items()},
            },
            "porchRequest": {
                "period": pmodel["period"],
                "episodes": pmodel["porch"]["episodes"],
                "pPorch365": round(pmodel["porch"]["p"], 4),
            },
            "vacant": {
                "period": xmodel["period"],
                "episodes": xmodel["sale"]["episodes"],
                "pSale365": round(xmodel["sale"]["p"], 4),
                "permitPeriod": xmodel["permitPeriod"],
                "permitEpisodes": xmodel["trades"]["general"]["episodes"],
                "pTrade730": {k: round(m["p"], 4) for k, m in xmodel["trades"].items()},
            },
            "closedRestaurant": {
                "period": rmodel["period"],
                "episodes": rmodel["episodes"],
                "closuresPerWeek": round(rmodel["closuresPerWeek"], 2),
                **{
                    name: {
                        "p365": round(m["conversion"], 4),
                        "baseline365": round(m["baseline"], 4),
                        "lift": round(m["lift"], 4),
                        "medianDays": round(m["median_days"], 1),
                        "daysP25": round(m["days_p25"], 1),
                        "daysP75": round(m["days_p75"], 1),
                    }
                    for name, m in (
                        ("license", rmodel["license"]),
                        ("licenseAfter30", rmodel["license_after30"]),
                        ("permit", rmodel["permit"]),
                    )
                },
            },
            "masonryAge": {
                "useCells": vmodel["masonry"]["use_cells"],
                "age": {
                    a: {"episodes": m["episodes"], "p365": round(m["p"], 4)}
                    for a, m in vmodel["masonry"]["age"].items()
                },
                "cells": {
                    f"{o}-{a}": {"episodes": m["episodes"], "p365": round(m["p"], 4)}
                    for (o, a), m in vmodel["masonry"]["cells"].items()
                },
            },
        },
        "leads": sorted(
            v_leads + s_leads + c_leads + pr_leads + vb_leads + cr_leads,
            key=lambda x: (x["signalDate"] or "", x["id"]),
            reverse=True,
        ),
        "recentWins": sorted(
            won,
            key=lambda x: (x["permitDate"], x["signalDate"], x["trade"], x["address"], x["contractor"] or ""),
            reverse=True,
        )[:400],
        "competitors": competitors(con, today, won),
        "areas": areas(con, today, dates["sales"]),
        "blocks": blocks,
        "commercial": {
            "preApplication": pre,
            "gcTargets": gc_targets(con, today),
            "newBusiness": {
                "model": new_business_summary(nbmodel),
                "spacesTotal": nb_total,
                "spaces": nb_spaces,
            },
            "openTrades": {
                "model": open_trades_summary(otmodel),
                "recentTotal": ot_total,
                "recent": ot_recent,
            },
        },
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(snapshot, default=str, separators=(",", ":"), ensure_ascii=False), encoding="utf-8"
    )
    print(
        f"wrote {out} ({out.stat().st_size / 1e6:.1f} MB): {len(v_leads)} violation leads, "
        f"{len(s_leads)} investor leads, {len(c_leads)} complaint leads, {len(pr_leads)} porch request leads, "
        f"{len(vb_leads)} vacant leads, {len(cr_leads)} closed restaurant leads, "
        f"{len(blocks['roofing'])} roofing blocks, "
        f"{len(pre['projects'])} pre-application projects, "
        f"{len(nb_spaces)} of {nb_total} new-business spaces ({nbmodel['signals']:,} historical signals, "
        f"{nbmodel['conversion'] * 100:.1f}% new license in a year, {nbmodel['lift']:.1f}x), "
        f"{len(ot_recent)} of {ot_total} recent $1M+ permits ({otmodel['signals']:,} historical, "
        f"{otmodel['conversion'] * 100:.1f}% sign/elevator/electrical follow-on)"
    )
    return snapshot


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    build(args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
