"""Build the client-facing lead snapshot from the warehouse.

    uv run python -m engine.leads.snapshot            # writes web/data/snapshot.json

Every probability shown to a client is a historical rate from the same records (Chicago, 2012 onward),
conditioned on how long ago the signal happened. Nothing is guessed: missing data stays missing.
"""

from __future__ import annotations

import argparse
import bisect
import json
import re
import sys
from datetime import UTC, date, datetime
from pathlib import Path

import duckdb

from engine.score.signals import (
    INVESTOR_RE,
    MAJOR,
    NON_OPERATOR_RE,
    PARCEL_FEATURES,
    build_parcel_features,
    fit_combo_rates,
    one,
    prepare_base,
    q,
)

DB = Path("data/warehouse.duckdb")
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
COMMERCIAL_SUB_TRADES = ("electrical", "plumbing", "hvac")

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


def title(s: str | None) -> str | None:
    if not s:
        return s
    return re.sub(r"\b([A-Z])([A-Z']*)\b", lambda m: m.group(1) + m.group(2).lower(), s)


def iso(d) -> str | None:
    return d.isoformat() if d else None


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
    return one(con, "SELECT max(issue_date) AS d FROM permits")["d"]


def as_of(con) -> dict:
    return one(
        con,
        """
        SELECT (SELECT max(issue_date) FROM permits) AS permits,
               (SELECT max(violation_date) FROM violations) AS violations,
               (SELECT max(sale_date) FROM sales) AS sales
    """,
    )


# ----------------------------------------------------------------------------------------------------------
def violation_model(con) -> dict:
    """Per trade and owner type: P(matching permit within 365 days) and delay distribution, 2012–2025."""
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
              SELECT ep.*, coalesce({COMPANY_SQL.format(col="par.owner_name")}, false) AS company
              FROM ep LEFT JOIN addr_parcel ap ON ap.address_key = ep.address_key
              LEFT JOIN parcels par ON par.pin10 = ap.pin10
            )
            SELECT o.company,
              min(p.issue_date - o.violation_date) AS days
            FROM o LEFT JOIN p ON p.address_key = o.address_key AND p.t_{t["permit"]}
              AND p.issue_date > o.violation_date AND p.issue_date <= o.violation_date + INTERVAL 365 DAY
            GROUP BY o.address_key, o.violation_date, o.company
        """,
        )
        entry = {}
        for owner in ("individual", "company"):
            sub = [r for r in rows if r["company"] == (owner == "company")]
            conv = [r["days"] for r in sub if r["days"] is not None]
            entry[owner] = {
                "episodes": len(sub),
                "p365": len(conv) / len(sub) if sub else 0.0,
                "delays": conv,
            }
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
            "delays": [r["first_days"] for r in sub if r["first_days"] is not None],
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
                     list(DISTINCT description) AS descriptions, min(id) AS violation_id,
                     bool_or(violation_status = 'OPEN') AS any_open,
                     count(*) AS citations, min(inspection_category) AS category,
                     avg(lat) AS lat, avg(lon) AS lon
              FROM recent GROUP BY address_key
            ),
            fresh AS (
              SELECT ep.* FROM ep
              WHERE NOT EXISTS (
                SELECT 1 FROM violations v WHERE v.address_key = ep.address_key AND v.t_{vt}
                  AND v.violation_date < ep.first_date AND v.violation_date >= ep.first_date - INTERVAL 365 DAY)
            )
            SELECT f.*, par.address, par.owner_name, par.owner_mailing, par.units, par.pin10,
              coalesce(ca.community_area, aa.community_area, pa.community_area, za.community_area)
                AS community_area,
              coalesce({COMPANY_SQL.format(col="par.owner_name")}, false) AS company,
              (SELECT min(p.issue_date) FROM p WHERE p.address_key = f.address_key AND p.t_{t["permit"]}
                 AND p.issue_date > f.first_date) AS permit_date,
              (SELECT first(pp.name_raw ORDER BY p.issue_date) FROM p
                 JOIN permit_parties pp ON pp.permit_id = p.id AND pp.role = '{t["role"]}'
                 WHERE p.address_key = f.address_key AND p.t_{t["permit"]} AND p.issue_date > f.first_date)
                AS permit_contractor
            FROM fresh f
            LEFT JOIN addr_parcel ap ON ap.address_key = f.address_key
            LEFT JOIN parcels par ON par.pin10 = ap.pin10
            LEFT JOIN ca_geom ca ON f.lat IS NOT NULL AND ST_Contains(ca.geom, ST_Point(f.lon, f.lat))
            LEFT JOIN addr_area aa ON aa.address_key = f.address_key
            LEFT JOIN pin_area pa ON pa.pin10 = ap.pin10
            LEFT JOIN zip_area za ON za.zip = par.zip
        """,
        )
        for r in rows:
            owner_type = "company" if r["company"] else "individual"
            m = vmodel[key][owner_type]
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
            p_rem = remaining_probability(m["p365"], m["delays"], age)
            ev = p_rem * WIN_RATE[owner_type] * values[key] * MARGIN
            tier = "act_now" if age <= 14 else "this_week" if age <= 45 else "monitor"
            leads.append(
                base
                | {
                    "id": f"v-{key}-{r['violation_id']}",
                    "kind": "violation",
                    "trades": [key],
                    "title": f"{TRADES[key]['label']} repair ordered",
                    "lat": r["lat"],
                    "lon": r["lon"],
                    "ageDays": age,
                    "tier": tier,
                    "probability": round(p_rem, 4),
                    "probabilityBasis": (
                        f"{m['p365'] * 100:.1f}% of similar {TRADES[key]['label'].lower()} violations at "
                        f"{owner_type}-owned properties led to a permitted repair within a year "
                        f"({m['episodes']:,} cases, 2012–2025); adjusted for {age} days already passed."
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
                    ],
                    "action": (
                        "Send a letter to the owner's mailing address this week, then follow up at weeks 6 and 12."
                        if owner_type == "individual"
                        else "Company-owned: look up the owner's business contact and call or email; mail as backup."
                    ),
                    "sourceUrl": (
                        "https://data.cityofchicago.org/resource/22u3-xenr.json?id=" + str(r["violation_id"])
                    ),
                }
            )
    return leads, won


def investor_leads(con, today_sales: date, smodel: dict) -> list[dict]:
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
          SELECT * FROM s WHERE sale_date > DATE '{today_sales}' - INTERVAL 240 DAY AND segment IS NOT NULL
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
          (SELECT list({{'name': name_raw, 'jobs': jobs}} ORDER BY jobs DESC)[:3] FROM used u
             WHERE u.buyer_key = r.buyer_key) AS contractors_used,
          (SELECT list(par2.address ORDER BY s2.sale_date DESC)[:5] FROM s s2
             JOIN parcels par2 ON par2.pin10 = s2.pin10
             WHERE s2.buyer_key = r.buyer_key AND s2.pin10 <> r.pin10
               AND s2.sale_date > DATE '{today_sales}' - INTERVAL 730 DAY) AS other_properties,
          (SELECT list({{'date': p.issue_date, 'type': p.permit_type, 'cost': p.reported_cost,
                         'description': left(p.description, 140)}} ORDER BY p.issue_date)[:3]
             FROM p WHERE p.pin10 = r.pin10 AND p.issue_date > r.sale_date) AS permits_since
        FROM recent r
        LEFT JOIN parcels par ON par.pin10 = r.pin10
        LEFT JOIN pin_area pa ON pa.pin10 = r.pin10
        LEFT JOIN zip_area za ON za.zip = par.zip
        LEFT JOIN repeat rp ON rp.buyer_key = r.buyer_key
    """,
    )
    leads = []
    for r in rows:
        m = smodel.get(r["segment"])
        if not m:
            continue
        age = (today_sales - r["sale_date"]).days
        started = bool(r["permits_since"])
        p_any = 1.0 if started else remaining_probability(m["p_any"], m["delays"], age)
        repeat = r["purchases_24m"] or 1
        tier = (
            "act_now" if repeat >= 3 and age <= 150 else "this_week" if age <= 120 or started else "monitor"
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
                    f"within a year ({m['purchases']:,} purchases, 2012–2025); adjusted for {age} days already passed."
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
        top AS (SELECT * FROM scored ORDER BY rate DESC, hash(pin10) LIMIT 150)
        SELECT t.*, par.address, par.owner_name, pa.community_area,
          (SELECT list({{'date': p.issue_date, 'type': p.permit_type, 'cost': p.reported_cost,
                         'description': left(p.description, 140)}} ORDER BY p.issue_date DESC)[:3]
             FROM p WHERE p.pin10 = t.pin10) AS recent_permits,
          (SELECT list(DISTINCT pp.name_raw)[:3] FROM p JOIN permit_parties pp ON pp.permit_id = p.id
             WHERE p.pin10 = t.pin10 AND pp.role = 'gc' AND p.issue_date > DATE '{today}' - INTERVAL 1095 DAY)
            AS recent_gcs
        FROM top t LEFT JOIN parcels par USING (pin10) LEFT JOIN pin_area pa USING (pin10)
        ORDER BY t.rate DESC
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
              SELECT gc, any_value(gc_name) AS gc_name, count(*) AS jobs_total,
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
              (SELECT list({{'name': sub_name, 'jobs': n}} ORDER BY n DESC)[:3] FROM (
                 SELECT any_value(sub_name) AS sub_name, count(*) AS n FROM jobs
                 WHERE jobs.gc = g.gc AND issue_date > DATE '{today}' - INTERVAL 730 DAY GROUP BY sub)) AS subs,
              (SELECT list(community_area ORDER BY n DESC)[:3] FROM (
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
              SELECT name_key, any_value(name_raw) AS name,
                count(DISTINCT id) FILTER (WHERE issue_date > DATE '{today}' - INTERVAL 365 DAY) AS jobs_12m,
                count(DISTINCT id) FILTER (WHERE issue_date <= DATE '{today}' - INTERVAL 365 DAY) AS jobs_prev,
                median(reported_cost) FILTER (WHERE reported_cost > 0) AS median_cost
              FROM x GROUP BY 1
            )
            SELECT c.*, c.jobs_12m / sum(c.jobs_12m) OVER () AS share,
              (SELECT list(community_area ORDER BY n DESC)[:3] FROM (
                 SELECT community_area, count(*) AS n FROM x WHERE x.name_key = c.name_key
                   AND community_area IS NOT NULL GROUP BY 1)) AS areas
            FROM c WHERE jobs_12m > 0 ORDER BY jobs_12m DESC LIMIT 25
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
                ({"name": n, "jobs": c} for n, c in won_counts.items()), key=lambda x: -x["jobs"]
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
    con = duckdb.connect(str(DB), read_only=True)
    con.execute("SET memory_limit = '8GB'")
    today = prepare(con)
    dates = as_of(con)
    print("models ...", flush=True)
    vmodel = violation_model(con)
    smodel = sale_model(con)
    values = job_values(con, today)
    print("violation leads ...", flush=True)
    v_leads, won = violation_leads(con, dates["violations"], vmodel, values)
    print("investor leads ...", flush=True)
    s_leads = investor_leads(con, dates["sales"], smodel)
    print("pre-application projects ...", flush=True)
    pre = preapp_projects(con, today)
    print("gc targets, competitors, areas ...", flush=True)
    snapshot = {
        "meta": {
            "generatedAt": datetime.now(UTC).isoformat(timespec="seconds"),
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
            ],
            "assumptions": {"winRate": WIN_RATE, "margin": MARGIN},
        },
        "trades": {k: {"label": t["label"], "jobValue": values[k]} for k, t in TRADES.items()},
        "models": {
            "violation": {
                k: {o: {"episodes": m["episodes"], "p365": round(m["p365"], 4)} for o, m in v.items()}
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
        },
        "leads": sorted(v_leads + s_leads, key=lambda x: x["signalDate"] or "", reverse=True),
        "recentWins": sorted(won, key=lambda x: x["permitDate"], reverse=True)[:400],
        "competitors": competitors(con, today, won),
        "areas": areas(con, today, dates["sales"]),
        "commercial": {"preApplication": pre, "gcTargets": gc_targets(con, today)},
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(snapshot, default=str, separators=(",", ":")))
    print(
        f"wrote {out} ({out.stat().st_size / 1e6:.1f} MB): {len(v_leads)} violation leads, "
        f"{len(s_leads)} investor leads, {len(pre['projects'])} pre-application projects"
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
