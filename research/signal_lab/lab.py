"""Signal lab: test creative lead hypotheses against Chicago history and rank them.

    uv run python research/signal_lab/lab.py              # all hypotheses
    uv run python research/signal_lab/lab.py H01 H06      # selected ones (writes *.partial.md/.json only)

Writes research/findings/signal-lab-<date>.md and .json. To add an idea, write one function that returns
`result(...)` using the helpers below and register it in HYPOTHESES.

Test types:
  * same_property: signal at a property -> target event at the same property within N days, against the
    same property's own earlier window (controls for "busy addresses").
  * neighborhood (grid cells ~160 m): does activity next door predict your own?
  * area before/after with a control group (storms).
  * cohort rates (building characteristics): annual event rate by group vs everyone.
"""

from __future__ import annotations

import json
import math
import sys
from collections.abc import Callable
from datetime import date
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from engine.score.food import RENO_PREDICATE  # noqa: E402
from engine.score.signals import INVESTOR_RE, NON_OPERATOR_RE, one, prepare_base, q  # noqa: E402

DB = Path("data/warehouse.duckdb")
OUT = Path("research/findings")
CELL_LAT, CELL_LON = 0.0015, 0.002  # ~167 m x ~165 m in Chicago
MIN_GROUP = 1000  # minimum properties for a cohort group to be reported


def result(
    hid: str, title: str, *, who: str, data: str, signal: str, target: str, metrics: dict, notes: str = ""
) -> dict:
    lift = metrics.get("lift")
    vol = metrics.get("signals_per_week")
    conv = metrics.get("conversion")
    if lift is None:
        verdict = "Descriptive"
    elif lift >= 3 and (vol or 0) >= 5:
        verdict = "Strong"
    elif lift >= 1.8:
        verdict = "Useful"
    elif lift >= 1.25:
        verdict = "Weak"
    else:
        verdict = "No signal"
    return {
        "id": hid,
        "title": title,
        "who": who,
        "data": data,
        "signal": signal,
        "target": target,
        "metrics": metrics,
        "verdict": verdict,
        "notes": notes,
        "score": (lift or 0) * min(1.0, (vol or 0) / 20) * (conv or 0) * 100,
    }


def prepare(con) -> None:
    prepare_base(con)
    # One point per address from every geocoded source, plus the parcel it belongs to.
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
        CREATE OR REPLACE TEMP TABLE pin_pt AS
        SELECT x.pin10, median(a.lat) AS lat, median(a.lon) AS lon,
               floor(median(a.lat) / {CELL_LAT})::BIGINT AS cy, floor(median(a.lon) / {CELL_LON})::BIGINT AS cx
        FROM (
          SELECT pin10, address_key FROM parcels WHERE address_key IS NOT NULL
          UNION ALL SELECT pin10, address_key FROM addr_pin
        ) x JOIN addr_pt a USING (address_key)
        GROUP BY 1
    """)
    con.execute("""
        CREATE OR REPLACE TEMP TABLE resi AS
        SELECT r.*, pt.cy, pt.cx FROM res_chars r JOIN pin_pt pt USING (pin10)
        WHERE r.class IN ('202','203','204','205','206','207','208','209','210','234','278','295','211','212')
    """)


def same_property(con, signal_sql: str, target_sql: str, window: int, start: str, end: str) -> dict:
    """signal_sql -> (k, d); target_sql -> (k, d). Episodes deduplicated to one per key per window."""
    con.execute(f"CREATE OR REPLACE TEMP TABLE sig AS {signal_sql}")
    con.execute(f"CREATE OR REPLACE TEMP TABLE tgt AS {target_sql}")
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE ep AS
        SELECT k, d FROM (
          SELECT k, d, lag(d) OVER (PARTITION BY k ORDER BY d) AS prev
          FROM (SELECT DISTINCT k, d FROM sig WHERE k IS NOT NULL AND d BETWEEN DATE '{start}' AND DATE '{end}')
        ) WHERE prev IS NULL OR d - prev > {window}
    """)
    r = one(
        con,
        f"""
        WITH o AS (
          SELECT e.k, e.d,
            min(t.d - e.d) FILTER (WHERE t.d > e.d AND t.d <= e.d + INTERVAL {window} DAY) AS days,
            bool_or(t.d > e.d - INTERVAL {2 * window} DAY AND t.d <= e.d - INTERVAL {window} DAY) AS before
          FROM ep e LEFT JOIN tgt t ON t.k = e.k
            AND t.d > e.d - INTERVAL {2 * window} DAY AND t.d <= e.d + INTERVAL {window} DAY
          GROUP BY ALL
        )
        SELECT count(*) AS signals,
          avg((days IS NOT NULL)::INT) AS conversion,
          avg(coalesce(before, false)::INT) AS baseline,
          median(days) AS median_days,
          count(*) FILTER (WHERE d > DATE '{end}' - INTERVAL 365 DAY) / 52.0 AS signals_per_week
        FROM o
    """,
    )
    r["lift"] = r["conversion"] / r["baseline"] if r["baseline"] else None
    by_year = q(
        con,
        f"""
        SELECT year(e.d) AS year, count(*) AS n,
          avg((EXISTS (SELECT 1 FROM tgt t WHERE t.k = e.k AND t.d > e.d AND t.d <= e.d + INTERVAL {window} DAY))::INT)
            AS conversion
        FROM ep e GROUP BY 1 ORDER BY 1
    """,
    )
    r["by_year"] = by_year
    return _round(r)


def _round_deep(x, digits: int = 5):
    """Round every float in nested results so the JSON file is byte-stable across runs."""
    if isinstance(x, float):
        return round(x, digits)
    if isinstance(x, dict):
        return {k: _round_deep(v, digits) for k, v in x.items()}
    if isinstance(x, list):
        return [_round_deep(v, digits) for v in x]
    return x


def _round(d: dict) -> dict:
    return {k: (round(v, 4) if isinstance(v, float) else v) for k, v in d.items()}


def permit_target(flag: str, key: str = "address_key") -> str:
    return f"SELECT {key} AS k, issue_date AS d FROM p WHERE t_{flag}"


# ----------------------------------------------------------------------------------------------------------
# Hypotheses
# ----------------------------------------------------------------------------------------------------------
def h01_solar_neighbors(con) -> dict:
    """Do neighbors going solar predict your own solar permit? (peer effect)"""
    rows = q(
        con,
        """
        WITH snap AS (SELECT unnest(generate_series(DATE '2020-01-01', DATE '2025-01-01', INTERVAL 1 YEAR))::DATE AS d),
        solar AS (SELECT p.pin10, p.issue_date FROM p WHERE t_solar AND pin10 IS NOT NULL),
        cell_prior AS (
          SELECT s.d, r.cy, r.cx, count(DISTINCT so.pin10) AS n
          FROM snap s JOIN solar so ON so.issue_date > s.d - INTERVAL 365 DAY AND so.issue_date <= s.d
          JOIN resi r ON r.pin10 = so.pin10 GROUP BY ALL
        ),
        u AS (
          SELECT s.d, r.pin10, coalesce(c.n, 0) AS neighbors_solar,
            EXISTS (SELECT 1 FROM solar x WHERE x.pin10 = r.pin10 AND x.issue_date <= s.d) AS already,
            EXISTS (SELECT 1 FROM solar x WHERE x.pin10 = r.pin10 AND x.issue_date > s.d
                    AND x.issue_date <= s.d + INTERVAL 365 DAY) AS y
          FROM snap s CROSS JOIN resi r LEFT JOIN cell_prior c ON c.d = s.d AND c.cy = r.cy AND c.cx = r.cx
        )
        SELECT CASE WHEN neighbors_solar = 0 THEN '0' WHEN neighbors_solar = 1 THEN '1' ELSE '2+' END AS grp,
          count(*) AS parcels, avg(y::INT) AS rate
        FROM u WHERE NOT already GROUP BY 1 ORDER BY 1
    """,
    )
    base = next(r["rate"] for r in rows if r["grp"] == "0")
    exposed = [r for r in rows if r["grp"] != "0"]
    exp_rate = sum(r["rate"] * r["parcels"] for r in exposed) / max(1, sum(r["parcels"] for r in exposed))
    top = next(r for r in rows if r["grp"] == "2+")
    vol = one(
        con,
        "SELECT count(*) / 52.0 AS v FROM p WHERE t_solar AND issue_date > (SELECT max(issue_date) FROM p) - INTERVAL 365 DAY",
    )["v"]
    return result(
        "H01",
        "Neighbors went solar → you go solar",
        who="Solar installers",
        data="Permits (solar), Assessor residential characteristics, geocoded addresses",
        signal="2+ solar permits on the same block (~160 m cell) in the past 12 months",
        target="Solar permit at a house/2–6 flat in the next 12 months",
        metrics=_round(
            {
                "by_neighbors": rows,
                "conversion": top["rate"],
                "baseline": base,
                "lift": top["rate"] / base if base else None,
                "any_neighbor_lift": exp_rate / base if base else None,
                "signals_per_week": vol,
            }
        ),
        notes="Cell-level exposure; confounded by neighborhood income and installer canvassing, so treat lift as an upper bound on true peer influence. Still directly usable for targeting.",
    )


def h02_reroof_then_solar(con) -> dict:
    """A brand-new roof is the cheapest moment to add solar."""
    rows = q(
        con,
        """
        WITH snap AS (SELECT unnest(generate_series(DATE '2019-01-01', DATE '2024-01-01', INTERVAL 1 YEAR))::DATE AS d),
        u AS (
          SELECT s.d, r.pin10,
            EXISTS (SELECT 1 FROM p WHERE p.pin10 = r.pin10 AND p.t_roofing AND NOT p.t_solar
                    AND p.issue_date > s.d - INTERVAL 365 DAY AND p.issue_date <= s.d) AS reroofed,
            EXISTS (SELECT 1 FROM p WHERE p.pin10 = r.pin10 AND p.t_solar AND p.issue_date <= s.d) AS already,
            EXISTS (SELECT 1 FROM p WHERE p.pin10 = r.pin10 AND p.t_solar AND p.issue_date > s.d
                    AND p.issue_date <= s.d + INTERVAL 730 DAY) AS y
          FROM snap s CROSS JOIN resi r
        )
        SELECT reroofed, count(*) AS parcels, avg(y::INT) AS rate FROM u WHERE NOT already GROUP BY 1 ORDER BY 1
    """,
    )
    on = next(r for r in rows if r["reroofed"])
    off = next(r for r in rows if not r["reroofed"])
    vol = one(
        con,
        "SELECT count(*) / 52.0 AS v FROM p WHERE t_roofing AND issue_date > (SELECT max(issue_date) FROM p) - INTERVAL 365 DAY",
    )["v"]
    return result(
        "H02",
        "New roof → solar within 2 years",
        who="Solar installers (and roofers partnering with them)",
        data="Permits (reroof, solar), Assessor residential characteristics",
        signal="Reroof permit in the past 12 months",
        target="Solar permit at the same parcel within 24 months",
        metrics=_round(
            {
                "conversion": on["rate"],
                "baseline": off["rate"],
                "lift": on["rate"] / off["rate"],
                "signals_per_week": vol,
                "groups": rows,
            }
        ),
    )


def h03_reroof_neighbors(con) -> dict:
    """Roofs on a block age (and get hit by storms) together."""
    rows = q(
        con,
        """
        WITH snap AS (SELECT unnest(generate_series(DATE '2016-01-01', DATE '2025-01-01', INTERVAL 3 MONTH))::DATE AS d),
        rr AS (SELECT p.pin10, p.issue_date FROM p WHERE t_roofing AND pin10 IS NOT NULL),
        cell_prior AS (
          SELECT s.d, r.cy, r.cx, count(DISTINCT rr.pin10) AS n
          FROM snap s JOIN rr ON rr.issue_date > s.d - INTERVAL 90 DAY AND rr.issue_date <= s.d
          JOIN resi r ON r.pin10 = rr.pin10 GROUP BY ALL
        ),
        u AS (
          SELECT s.d, r.pin10, coalesce(c.n, 0) AS n,
            EXISTS (SELECT 1 FROM rr x WHERE x.pin10 = r.pin10 AND x.issue_date > s.d - INTERVAL 90 DAY AND x.issue_date <= s.d) AS self_recent,
            EXISTS (SELECT 1 FROM rr x WHERE x.pin10 = r.pin10 AND x.issue_date > s.d AND x.issue_date <= s.d + INTERVAL 180 DAY) AS y
          FROM snap s CROSS JOIN resi r LEFT JOIN cell_prior c ON c.d = s.d AND c.cy = r.cy AND c.cx = r.cx
        )
        SELECT CASE WHEN n = 0 THEN '0' WHEN n = 1 THEN '1' ELSE '2+' END AS grp, count(*) AS parcels, avg(y::INT) AS rate
        FROM u WHERE NOT self_recent GROUP BY 1 ORDER BY 1
    """,
    )
    base = next(r["rate"] for r in rows if r["grp"] == "0")
    top = next(r for r in rows if r["grp"] == "2+")
    return result(
        "H03",
        "Neighbors re-roofed → you re-roof",
        who="Roofers",
        data="Permits (reroof), Assessor residential characteristics",
        signal="2+ reroof permits on the same block in the past 90 days",
        target="Reroof permit at a neighboring house in the next 180 days",
        metrics=_round(
            {
                "by_neighbors": rows,
                "conversion": top["rate"],
                "baseline": base,
                "lift": top["rate"] / base,
                "signals_per_week": None,
            }
        ),
        notes="Block-level targeting for door hangers and mail right after a cluster of permits.",
    )


def h04_storms(con, event_type: str, min_mag: float, hid: str, title: str) -> dict:
    """Area before/after with control: permits in cells near a storm report vs the same window a year earlier,
    compared with all other cells over the same windows (difference in ratios)."""
    rows = q(
        con,
        f"""
        WITH ev AS (
          SELECT event_date, lat, lon FROM storms
          WHERE event_type = '{event_type}' AND magnitude >= {min_mag}
            AND lat BETWEEN 41.64 AND 42.03 AND lon BETWEEN -87.95 AND -87.52
            AND event_date BETWEEN DATE '2012-01-01' AND DATE '2025-06-30'
        ),
        cells AS (SELECT DISTINCT cy, cx FROM resi),
        hit AS (
          SELECT ev.event_date, c.cy, c.cx,
            -- within ~3 km of the report
            (abs(c.cy * {CELL_LAT} - ev.lat) < 0.027 AND abs(c.cx * {CELL_LON} - ev.lon) < 0.036) AS near
          FROM ev CROSS JOIN cells c
        ),
        rr AS (SELECT r.cy, r.cx, p.issue_date FROM p JOIN resi r USING (pin10) WHERE p.t_roofing)
        SELECT h.near,
          count(*) FILTER (WHERE rr.issue_date > h.event_date AND rr.issue_date <= h.event_date + INTERVAL 120 DAY) AS after_n,
          count(*) FILTER (WHERE rr.issue_date > h.event_date - INTERVAL 365 DAY
                           AND rr.issue_date <= h.event_date - INTERVAL 245 DAY) AS year_before_n
        FROM hit h LEFT JOIN rr ON rr.cy = h.cy AND rr.cx = h.cx
          AND rr.issue_date > h.event_date - INTERVAL 365 DAY AND rr.issue_date <= h.event_date + INTERVAL 120 DAY
        GROUP BY 1
    """,
    )
    near = next((r for r in rows if r["near"]), None)
    far = next((r for r in rows if not r["near"]), None)
    events = one(
        con,
        f"SELECT count(*) AS n FROM storms WHERE event_type = '{event_type}' AND magnitude >= {min_mag} AND lat BETWEEN 41.64 AND 42.03 AND lon BETWEEN -87.95 AND -87.52 AND event_date BETWEEN DATE '2012-01-01' AND DATE '2025-06-30'",
    )["n"]
    if not near or not far or not near["year_before_n"] or not far["year_before_n"]:
        return result(
            hid,
            title,
            who="Roofers",
            data="NOAA Storm Events, permits",
            signal=f"{event_type} ≥ {min_mag}",
            target="Reroof permits",
            metrics={"events": events, "lift": None},
            notes="Not enough events.",
        )
    r_near = near["after_n"] / near["year_before_n"]
    r_far = far["after_n"] / far["year_before_n"]
    return result(
        hid,
        title,
        who="Roofers, gutter and siding contractors, restoration",
        data="NOAA Storm Events (Cook County reports with coordinates), permits",
        signal=f"{event_type} report ≥ {min_mag}{' in' if event_type == 'Hail' else ' kt'} within ~3 km",
        target="Reroof permits on those blocks in the next 120 days (vs the same blocks a year earlier, vs all other blocks)",
        metrics=_round(
            {
                "storm_reports": events,
                "near_after": near["after_n"],
                "near_year_before": near["year_before_n"],
                "far_after": far["after_n"],
                "far_year_before": far["year_before_n"],
                "conversion": r_near,
                "baseline": r_far,
                "lift": r_near / r_far,
                "signals_per_week": events / (13.5 * 52),
            }
        ),
        notes="'conversion' and 'baseline' here are after/before permit ratios near vs far from the storm; lift is their ratio (difference-in-ratios). Spotter reports are points, so 3 km is a rough footprint.",
    )


def h05_hail(con) -> dict:
    return h04_storms(con, "Hail", 1.0, "H04", "Hail ≥ 1 inch → reroof wave")


def h05b_wind(con) -> dict:
    return h04_storms(con, "Thunderstorm Wind", 60, "H05", "Damaging wind (60+ kt) → reroof wave")


def sr_signal(sr_type: str) -> str:
    return (
        f"SELECT address_key AS k, created_date AS d FROM sr311 WHERE sr_type = '{sr_type}' AND NOT duplicate"
    )


def h06_basement_water(con) -> dict:
    m = same_property(
        con,
        sr_signal("Water in Basement Complaint"),
        permit_target("plumbing"),
        365,
        "2016-01-01",
        "2025-10-31",
    )
    return result(
        "H06",
        "311 'water in basement' → plumbing work",
        who="Plumbers, waterproofing and drain contractors",
        data="311 service requests, permits",
        signal="Resident files a 'Water in Basement' 311 complaint",
        target="Plumbing permit at the same address within 365 days",
        metrics=m,
        notes="Permits undercount drain/waterproofing jobs (many need no permit), so this is a floor.",
    )


def h07_complaint_to_violation(con) -> dict:
    m = same_property(
        con,
        sr_signal("Building Violation"),
        "SELECT address_key AS k, violation_date AS d FROM violations",
        120,
        "2016-01-01",
        "2025-10-31",
    )
    # Complaints don't name a trade; measure which trades the resulting citations fall in.
    trades = ["porch", "masonry", "roofing", "windows_doors", "plumbing", "electrical", "hvac"]
    m["groups"] = q(
        con,
        f"""
        SELECT {", ".join(f"avg((EXISTS (SELECT 1 FROM violations v WHERE v.address_key = ep.k AND v.t_{t} AND v.violation_date > ep.d AND v.violation_date <= ep.d + INTERVAL 120 DAY))::INT) AS {t}_rate" for t in trades)}
        FROM ep
    """,
    )
    return result(
        "H07",
        "311 building complaint → city citation (earlier lead)",
        who="Porch, masonry, roofing, general repair contractors",
        data="311 service requests, building violations",
        signal="'Building Violation' 311 complaint at an address",
        target="Building violation recorded at the same address within 120 days",
        metrics=m,
        notes="If conversion is high, the complaint is an earlier version of the violation lead (median_days = head start).",
    )


def h08_porch_request(con) -> dict:
    m = same_property(
        con, sr_signal("Porch Inspection Request"), permit_target("porch"), 365, "2016-01-01", "2025-10-31"
    )
    return result(
        "H08",
        "311 porch inspection request → porch permit",
        who="Porch builders",
        data="311 service requests, permits",
        signal="'Porch Inspection Request' 311 call",
        target="Porch permit at the same address within 365 days",
        metrics=m,
    )


def h09_vacant_to_sale(con) -> dict:
    m = same_property(
        con,
        "SELECT a.pin10 AS k, s.created_date AS d FROM sr311 s JOIN addr_pin a USING (address_key) WHERE s.sr_type = 'Vacant/Abandoned Building Complaint' AND NOT s.duplicate",
        "SELECT pin10 AS k, sale_date AS d FROM sales WHERE NOT filtered_out",
        365,
        "2016-01-01",
        "2025-06-30",
    )
    return result(
        "H09",
        "Vacant-building complaint → property sells",
        who="Investors' contractors, rehab GCs, property managers (and investors themselves)",
        data="311 service requests, Cook County sales",
        signal="'Vacant/Abandoned Building' 311 complaint",
        target="Property sale within 365 days",
        metrics=m,
        notes="A sale after vacancy usually means a rehab: an early entry into the investor-purchase lead.",
    )


def h10_unpermitted_work(con) -> dict:
    m = same_property(
        con,
        sr_signal("No Building Permit and Construction Violation"),
        "SELECT address_key AS k, issue_date AS d FROM p",
        180,
        "2016-01-01",
        "2025-10-31",
    )
    return result(
        "H10",
        "Complaint about unpermitted work → permit gets pulled",
        who="Expediters, architects, GCs who legalize work",
        data="311 service requests, permits",
        signal="'No Building Permit and Construction Violation' 311 complaint",
        target="Any permit at the same address within 180 days",
        metrics=m,
    )


def h11_lead_test(con) -> dict:
    m = same_property(
        con,
        sr_signal("Water Lead Test Kit Request"),
        permit_target("plumbing"),
        365,
        "2016-01-01",
        "2025-10-31",
    )
    return result(
        "H11",
        "Lead test kit request → plumbing work",
        who="Plumbers",
        data="311 service requests, permits",
        signal="Household requests a water lead test kit",
        target="Plumbing permit at the same address within 365 days",
        metrics=m,
        notes="Lead service line replacements are done under the Water Department, not building permits, so this measures only other plumbing work.",
    )


def cohort(con, hid: str, title: str, who: str, group_sql: str, flag: str, notes: str = "") -> dict:
    """Annual permit rate (2023-2025 average) by property group vs all residential parcels."""
    rows = q(
        con,
        f"""
        WITH t AS (
          SELECT DISTINCT pin10, year(issue_date) AS y FROM p
          WHERE t_{flag} AND issue_date BETWEEN DATE '2023-01-01' AND DATE '2025-12-31'
        ),
        g AS (SELECT pin10, {group_sql} AS grp FROM resi)
        SELECT grp, count(*) AS parcels,
          (SELECT count(*) FROM t JOIN g g2 USING (pin10) WHERE g2.grp = g.grp) / (3.0 * count(*)) AS annual_rate
        FROM g WHERE grp IS NOT NULL GROUP BY grp ORDER BY annual_rate DESC
    """,
    )
    total = sum(r["parcels"] for r in rows)
    overall = sum(r["annual_rate"] * r["parcels"] for r in rows) / total
    for r in rows:
        r["lift"] = round(r["annual_rate"] / overall, 2) if overall else None
    # Small groups produce noisy rates; only groups with enough properties can headline.
    rows = [r for r in rows if r["parcels"] >= MIN_GROUP]
    top = rows[0]
    return result(
        hid,
        title,
        who=who,
        data="Cook County Assessor residential characteristics, permits",
        signal=f"Property group: {top['grp']}",
        target=f"{flag.replace('_', ' ')} permit per year",
        metrics=_round(
            {
                "groups": rows,
                "overall_annual_rate": overall,
                "conversion": top["annual_rate"],
                "baseline": overall,
                "lift": top["annual_rate"] / overall,
                "signals_per_week": None,
            }
        ),
        notes=notes,
    )


def h12_roof_age(con) -> dict:
    return cohort(
        con,
        "H12",
        "Which houses re-roof: age × roof material",
        "Roofers, solar installers",
        """CASE WHEN year_built IS NULL THEN NULL
             ELSE (CASE WHEN year_built < 1910 THEN 'pre-1910' WHEN year_built < 1940 THEN '1910-39'
                        WHEN year_built < 1970 THEN '1940-69' WHEN year_built < 2000 THEN '1970-99' ELSE '2000+' END)
                  || ' / ' || coalesce(roof, 'unknown') END""",
        "roofing",
    )


def h13_masonry_walls(con) -> dict:
    return cohort(
        con,
        "H13",
        "Which buildings need masonry work: walls × age",
        "Masons, tuckpointers",
        """CASE WHEN year_built IS NULL OR ext_wall IS NULL THEN NULL
             ELSE ext_wall || ' / ' || (CASE WHEN year_built < 1910 THEN 'pre-1910' WHEN year_built < 1940 THEN '1910-39'
                        WHEN year_built < 1970 THEN '1940-69' ELSE '1970+' END) END""",
        "masonry",
    )


def h14_no_ac(con) -> dict:
    return cohort(
        con,
        "H14",
        "Which homes pull HVAC permits: A/C × heat type",
        "HVAC contractors",
        "CASE WHEN air IS NULL THEN NULL ELSE air || ' / ' || coalesce(heat, 'unknown heat') END",
        "hvac",
        notes="The original idea (no central A/C → new A/C installs) is refuted: homes without central A/C are below average. Homes that already have it pull more permits, i.e. replacements. Most residential HVAC swaps aren't permitted, so rates are low.",
    )


def h15_condition(con) -> dict:
    return cohort(
        con,
        "H15",
        "Assessor condition rating → renovation permits",
        "General contractors, rehab crews",
        "repair_condition",
        "interior_buildout",
    )


def h16_energy(con) -> dict:
    rows = q(
        con,
        """
        WITH b AS (
          SELECT DISTINCT building_id, address_key, data_year, energy_star_score,
            CASE WHEN energy_star_score <= 40 THEN 'ENERGY STAR ≤ 40'
                 WHEN energy_star_score >= 75 THEN 'ENERGY STAR ≥ 75'
                 ELSE '41-74' END AS grp
          FROM benchmarking WHERE energy_star_score IS NOT NULL AND data_year BETWEEN 2016 AND 2022
        ),
        o AS (
          SELECT b.grp, b.building_id, b.data_year,
            EXISTS (SELECT 1 FROM p WHERE p.address_key = b.address_key AND (p.t_hvac OR p.t_electrical)
                    AND year(p.issue_date) BETWEEN b.data_year + 1 AND b.data_year + 2) AS y
          FROM b
        )
        SELECT grp, count(*) AS building_years, avg(y::INT) AS rate FROM o GROUP BY 1 ORDER BY rate DESC
    """,
    )
    low = next(r for r in rows if r["grp"].startswith("ENERGY STAR ≤"))
    high = next(r for r in rows if r["grp"].startswith("ENERGY STAR ≥"))
    return result(
        "H16",
        "Poor energy score → mechanical/electrical upgrades",
        who="Commercial HVAC, electrical, lighting retrofit, energy services",
        data="Chicago Energy Benchmarking (buildings ≥ 50k sq ft), permits",
        signal="Building reports an ENERGY STAR score ≤ 40",
        target="HVAC or electrical permit in the following two years",
        metrics=_round(
            {
                "groups": rows,
                "conversion": low["rate"],
                "baseline": high["rate"],
                "lift": low["rate"] / high["rate"],
                "signals_per_week": None,
            }
        ),
        notes="Large buildings; addresses matched by normalized street address.",
    )


CHAIN_TARGET = "SELECT address_key AS k, issue_date AS d FROM p WHERE t_porch OR t_masonry"


def h17_complaint_chain(con) -> dict:
    """311 complaint -> porch/masonry citation -> porch/masonry permit, with timing for each step."""

    def complaints(negate: str) -> str:
        return f"""
        SELECT s.address_key AS k, s.created_date AS d FROM sr311 s
        WHERE s.sr_type = 'Building Violation' AND NOT s.duplicate AND s.address_key IS NOT NULL
          AND {negate} EXISTS (SELECT 1 FROM violations v WHERE v.address_key = s.address_key
                      AND (v.t_porch OR v.t_masonry) AND v.violation_date > s.created_date
                      AND v.violation_date <= s.created_date + INTERVAL 120 DAY)
    """

    signal = complaints("")
    uncited = same_property(con, complaints("NOT"), CHAIN_TARGET, 365, "2018-07-01", "2025-10-31")
    m = same_property(con, signal, CHAIN_TARGET, 365, "2018-07-01", "2025-10-31")
    steps = []
    for label, vflag, pflag in (
        (
            "Porch or masonry citation → porch or masonry permit",
            "t_porch OR t_masonry",
            "t_porch OR t_masonry",
        ),
        ("Porch citation → porch permit", "t_porch", "t_porch"),
        ("Masonry citation → masonry permit", "t_masonry", "t_masonry"),
    ):
        row = one(
            con,
            f"""
            WITH c AS (
              SELECT e.k, e.d, min(v.violation_date) AS vd
              FROM ep e JOIN violations v ON v.address_key = e.k AND ({vflag})
                AND v.violation_date > e.d AND v.violation_date <= e.d + INTERVAL 120 DAY
              GROUP BY ALL
            ),
            pv AS (
              SELECT c.k, c.d, c.vd, min(t.issue_date) AS pd
              FROM c LEFT JOIN p t ON t.address_key = c.k AND ({pflag})
                AND t.issue_date > c.vd AND t.issue_date <= c.vd + INTERVAL 365 DAY
              GROUP BY ALL
            )
            SELECT count(*) AS complaints, median(vd - d) AS median_days_complaint_to_citation,
              round(avg((pd IS NOT NULL)::INT), 4) AS conversion, count(pd) AS permits,
              median(pd - vd) AS median_days_citation_to_permit,
              quantile_cont(pd - vd, 0.25) AS citation_to_permit_p25_days,
              quantile_cont(pd - vd, 0.75) AS citation_to_permit_p75_days,
              median(pd - d) AS median_days_complaint_to_permit
            FROM pv
        """,
        )
        steps.append({"step": label, **row})
    m["groups"] = steps
    m["complaint_basis"] = [
        {
            "cohort": "Complaint followed by a porch/masonry citation within 120 days",
            "complaints": m["signals"],
            "conversion": m["conversion"],
            "prior_window": m["baseline"],
            "median_days_complaint_to_permit": m["median_days"],
        },
        {
            "cohort": "Complaint with NO porch/masonry citation within 120 days",
            "complaints": uncited["signals"],
            "conversion": uncited["conversion"],
            "prior_window": uncited["baseline"],
            "median_days_complaint_to_permit": uncited["median_days"],
        },
    ]
    m["lift_note"] = (
        "lift = permit within 365 days of the complaint vs the same address's window 1-2 years earlier"
    )
    return result(
        "H17",
        "Complaint chain: 311 complaint → porch/masonry citation → permit (when to mail)",
        who="Porch builders, masons and tuckpointers",
        data="311 service requests, building violations, permits",
        signal="'Building Violation' 311 complaint at an address that gets a porch or masonry citation within 120 days",
        target="Porch or masonry permit at the same address within 365 days of the complaint",
        metrics=m,
        notes="Cohort is selected on the citation (known only afterwards), so it describes the timeline of the chain, not a "
        "forecast available on the complaint day; at complaint time the usable rate is H07 (31.6% cited) times the "
        "porch/masonry share. 311 data starts mid-2018. The citation-to-permit step is the validated violation lead; "
        "lift against the address's own earlier year is inflated by the citation itself forcing a repair, so also read the "
        "complaint_basis table (complaints with no porch/masonry citation convert at a much lower rate). "
        "Permits undercount repairs, so rates are floors.",
    )


def h18_repeat_investors(con) -> dict:
    """Company buyers with 3+ purchase dates in the prior 24 months vs one-off company buyers."""
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE co_sales AS
        SELECT DISTINCT upper(trim(buyer_name)) AS buyer, pin10, sale_date, is_multisale FROM sales
        WHERE NOT filtered_out AND buyer_name IS NOT NULL AND pin10 IS NOT NULL
          AND sale_date BETWEEN DATE '2014-01-01' AND DATE '2025-10-31'
          AND regexp_matches(upper(buyer_name), '{INVESTOR_RE}')
          AND NOT regexp_matches(upper(buyer_name), '{NON_OPERATOR_RE}')
    """)
    con.execute("""
        CREATE OR REPLACE TEMP TABLE co_deals AS SELECT DISTINCT buyer, sale_date FROM co_sales
    """)
    con.execute("""
        CREATE OR REPLACE TEMP TABLE co_units AS
        SELECT u.buyer, u.pin10, u.sale_date,
          (SELECT count(*) FROM co_deals d WHERE d.buyer = u.buyer AND d.sale_date > u.sale_date - INTERVAL 730 DAY
             AND d.sale_date <= u.sale_date) AS n24
        FROM co_sales u
        WHERE NOT u.is_multisale AND u.sale_date >= DATE '2016-01-01'
    """)
    con.execute("""
        CREATE OR REPLACE TEMP TABLE co_out AS
        SELECT u.buyer, u.pin10, u.sale_date, u.n24,
          CASE WHEN u.n24 = 1 THEN '1 purchase' WHEN u.n24 = 2 THEN '2 purchases'
               WHEN u.n24 <= 5 THEN '3-5 purchases' ELSE '6+ purchases' END AS grp,
          min(p.issue_date) AS first_permit
        FROM co_units u LEFT JOIN p ON p.pin10 = u.pin10 AND p.issue_date > u.sale_date
          AND p.issue_date <= u.sale_date + INTERVAL 365 DAY
        GROUP BY ALL
    """)
    groups = q(
        con,
        """
        SELECT grp, count(*) AS purchases, count(DISTINCT buyer) AS buyers,
          avg((first_permit IS NOT NULL)::INT) AS conversion,
          median(first_permit - sale_date) AS median_days_to_first_permit
        FROM co_out GROUP BY 1 ORDER BY min(n24)
    """,
    )
    agg = one(
        con,
        """
        SELECT
          avg((first_permit IS NOT NULL)::INT) FILTER (WHERE n24 >= 3) AS repeat_rate,
          avg((first_permit IS NOT NULL)::INT) FILTER (WHERE n24 = 1) AS single_rate,
          count(*) FILTER (WHERE n24 >= 3) AS repeat_purchases,
          count(DISTINCT buyer) FILTER (WHERE n24 >= 3) AS repeat_buyers,
          count(*) FILTER (WHERE n24 = 1) AS single_purchases,
          median(first_permit - sale_date) FILTER (WHERE n24 >= 3) AS repeat_median_days,
          median(first_permit - sale_date) FILTER (WHERE n24 = 1) AS single_median_days,
          count(*) FILTER (WHERE n24 >= 3 AND sale_date > DATE '2025-10-31' - INTERVAL 365 DAY) / 52.0 AS per_week
        FROM co_out
    """,
    )
    con.execute("""
        CREATE OR REPLACE TEMP TABLE co_gc AS
        SELECT DISTINCT o.buyer, o.pin10, o.n24, p.id AS permit_id, p.issue_date, pp.name_key AS gc
        FROM co_out o JOIN p ON p.pin10 = o.pin10 AND p.issue_date > o.sale_date
          AND p.issue_date <= o.sale_date + INTERVAL 365 DAY
        JOIN permit_parties pp ON pp.permit_id = p.id AND pp.role = 'gc' AND pp.name_key IS NOT NULL
    """)
    con.execute("""
        CREATE OR REPLACE TEMP TABLE gc_share AS
        WITH c AS (
          SELECT year(p.issue_date) AS y, pp.name_key AS gc, count(DISTINCT p.id) AS n
          FROM p JOIN permit_parties pp ON pp.permit_id = p.id AND pp.role = 'gc' AND pp.name_key IS NOT NULL
          WHERE p.issue_date >= DATE '2016-01-01' GROUP BY ALL
        )
        SELECT y, gc, n / sum(n) OVER (PARTITION BY y) AS share FROM c
    """)
    loyal = one(
        con,
        """
        WITH x AS (
          SELECT DISTINCT g.buyer, g.permit_id, g.gc, g.issue_date, g.pin10,
            EXISTS (SELECT 1 FROM co_gc h WHERE h.buyer = g.buyer AND h.pin10 <> g.pin10 AND h.issue_date < g.issue_date)
              AS has_prior,
            EXISTS (SELECT 1 FROM co_gc h WHERE h.buyer = g.buyer AND h.pin10 <> g.pin10 AND h.issue_date < g.issue_date
                    AND h.gc = g.gc) AS same_gc
          FROM co_gc g WHERE g.n24 >= 3
        ),
        b AS (
          SELECT x.permit_id, x.buyer,
            (SELECT coalesce(sum(m.share), 0) FROM (
               SELECT DISTINCT h.gc FROM co_gc h
               WHERE h.buyer = x.buyer AND h.pin10 <> x.pin10 AND h.issue_date < x.issue_date) hs
             JOIN gc_share m ON m.gc = hs.gc AND m.y = year(x.issue_date)) AS chance
          FROM x WHERE x.has_prior
        )
        SELECT count(*) AS repeat_permits_with_gc, count(*) FILTER (WHERE has_prior) AS with_prior_gc_history,
          avg(same_gc::INT) FILTER (WHERE has_prior) AS loyalty_share,
          count(DISTINCT buyer) FILTER (WHERE has_prior) AS buyers,
          (SELECT avg(chance) FROM b) AS random_gc_chance
        FROM x
    """,
    )
    loyalty = [
        {
            "measure": "Repeat buyers' permits naming a GC the buyer used before on another property",
            "permits": loyal["with_prior_gc_history"],
            "buyers": loyal["buyers"],
            "share": loyal["loyalty_share"],
        },
        {
            "measure": "Benchmark: chance a randomly drawn Chicago GC (same year) would be one of those GCs",
            "permits": loyal["with_prior_gc_history"],
            "buyers": loyal["buyers"],
            "share": loyal["random_gc_chance"],
        },
    ]
    for r in loyalty:
        r["share"] = round(r["share"], 4)
    return result(
        "H18",
        "Repeat investors (3+ purchases in 24 months) renovate more and faster than one-off company buyers",
        who="Rehab GCs, subs working for investors, property managers",
        data="Cook County sales, permits, permit parties",
        signal="Company buyer (not bank/agency/land trust) who bought on 3+ distinct dates in the 24 months up to and including this purchase",
        target="Any permit at the purchased parcel within 365 days of purchase (baseline: company buyers with exactly 1 purchase date in 24 months)",
        metrics=_round(
            {
                "groups": groups,
                "conversion": agg["repeat_rate"],
                "baseline": agg["single_rate"],
                "lift": agg["repeat_rate"] / agg["single_rate"] if agg["single_rate"] else None,
                "signals_per_week": agg["per_week"],
                "repeat_median_days_to_permit": agg["repeat_median_days"],
                "single_median_days_to_permit": agg["single_median_days"],
                "repeat_buyers": agg["repeat_buyers"],
                "repeat_purchases": agg["repeat_purchases"],
                "single_purchases": agg["single_purchases"],
                "loyalty": loyalty,
            }
        ),
        notes="Buyers are identified by name string (the sales feed truncates names to ~25 characters and investors "
        "often use a new LLC per building), so portfolio operators are undercounted and 'repeat' means a repeat name. "
        "Units are single-parcel deeds (multi-parcel deeds are excluded as units but count as one purchase date). "
        "Repeat investors differ from one-off buyers in building mix (more multi-family/commercial and larger "
        "parcels that need permits for any reason), so this is a targeting comparison, not a causal effect. "
        "GC loyalty: of repeat buyers' permits naming a GC where the buyer already had an earlier permit with a named GC on "
        "a different property, the share naming one of those same GCs, against the chance a random GC (weighted by "
        "that year's citywide GC permit share) would match. Only buyers with prior permits can be measured, which "
        "favors buyers who renovate repeatedly.",
    )


def h19_tree_emergency(con) -> dict:
    m = same_property(
        con,
        sr_signal("Tree Emergency"),
        "SELECT address_key AS k, issue_date AS d FROM p WHERE t_roofing OR t_porch",
        180,
        "2018-07-01",
        "2025-10-31",
    )
    season = one(
        con,
        """
        SELECT avg((EXISTS (SELECT 1 FROM tgt t WHERE t.k = e.k AND t.d > e.d - INTERVAL 365 DAY
                            AND t.d <= e.d - INTERVAL 185 DAY))::INT) AS r
        FROM ep e
    """,
    )["r"]
    m["seasonal_baseline"] = season
    m["seasonal_lift"] = m["conversion"] / season if season else None
    m["groups"] = q(
        con,
        """
        SELECT 'roofing' AS target, avg((EXISTS (SELECT 1 FROM p t WHERE t.address_key = e.k AND t.t_roofing
              AND t.issue_date > e.d AND t.issue_date <= e.d + INTERVAL 180 DAY))::INT) AS conversion,
          avg((EXISTS (SELECT 1 FROM p t WHERE t.address_key = e.k AND t.t_roofing
              AND t.issue_date > e.d - INTERVAL 365 DAY AND t.issue_date <= e.d - INTERVAL 185 DAY))::INT)
            AS seasonal_baseline_rate
        FROM ep e
        UNION ALL
        SELECT 'porch', avg((EXISTS (SELECT 1 FROM p t WHERE t.address_key = e.k AND t.t_porch
              AND t.issue_date > e.d AND t.issue_date <= e.d + INTERVAL 180 DAY))::INT),
          avg((EXISTS (SELECT 1 FROM p t WHERE t.address_key = e.k AND t.t_porch
              AND t.issue_date > e.d - INTERVAL 365 DAY AND t.issue_date <= e.d - INTERVAL 185 DAY))::INT)
        FROM ep e
    """,
    )
    return result(
        "H19",
        "311 'tree emergency' → roofing or porch permit (storm-damage proxy)",
        who="Tree services, roofers, porch builders",
        data="311 service requests, permits",
        signal="'Tree Emergency' 311 request (fallen/hazardous tree) at an address",
        target="Roofing or porch permit at the same address within 180 days",
        metrics=_round(m),
        notes="Tree emergencies cluster in storm weeks and summer, and roofing permits are seasonal, so the default "
        "baseline (the 180 days before the prior window) can be season-shifted; 'seasonal_baseline' uses the same "
        "180-day window one year earlier and is the fairer control. A tree on a roof is often repaired by insurance "
        "without a permit, and the 311 address is often the parkway tree in front of the house, not a damaged building.",
    )


def h20_rodent_to_violation(con) -> dict:
    m = same_property(
        con,
        sr_signal("Rodent Baiting/Rat Complaint"),
        "SELECT address_key AS k, violation_date AS d FROM violations",
        180,
        "2018-07-01",
        "2025-10-31",
    )
    m["groups"] = q(
        con,
        """
        SELECT 'pest/sanitation violation' AS target,
          avg((EXISTS (SELECT 1 FROM violations v WHERE v.address_key = e.k AND v.t_pest
              AND v.violation_date > e.d AND v.violation_date <= e.d + INTERVAL 180 DAY))::INT) AS conversion,
          avg((EXISTS (SELECT 1 FROM violations v WHERE v.address_key = e.k AND v.t_pest
              AND v.violation_date > e.d - INTERVAL 360 DAY AND v.violation_date <= e.d - INTERVAL 180 DAY))::INT)
            AS baseline_rate
        FROM ep e
    """,
    )
    return result(
        "H20",
        "311 rodent complaint → building/pest violation (pest-control demand proxy)",
        who="Pest control, sanitation and property-management services",
        data="311 service requests, building violations",
        signal="'Rodent Baiting/Rat Complaint' 311 request at an address",
        target="Any building violation at the same address within 180 days",
        metrics=m,
        notes="The restaurant-inspection version of the pest idea is H23 (food inspections, added in round 3). Rat "
        "complaints are filed against the address of the nearby problem (alleys, garbage), not necessarily the "
        "owner's building, and baiting is done by the City, so the complaint is demand evidence, not a work order.",
    )


def h21_food_takeover(con) -> dict:
    con.execute("""
        CREATE OR REPLACE TEMP TABLE fl AS
        SELECT account_number, address_key, min(issue_date) AS d FROM food_licenses
        WHERE address_key IS NOT NULL AND issue_date IS NOT NULL GROUP BY ALL
    """)
    con.execute("""
        CREATE OR REPLACE TEMP TABLE fl_x AS
        SELECT f.account_number, f.address_key, f.d,
          EXISTS (SELECT 1 FROM p WHERE p.address_key = f.address_key AND p.issue_date > f.d - INTERVAL 730 DAY
                  AND p.issue_date <= f.d AND (p.t_interior_buildout OR p.t_new_construction
                       OR p.permit_type IN ('PERMIT - NEW CONSTRUCTION', 'PERMIT - RENOVATION/ALTERATION')))
            AS had_buildout,
          min(a.issue_date) AS first_permit,
          bool_or(a.t_signs) AS sign,
          bool_or(a.t_interior_buildout OR a.t_new_construction
                  OR a.permit_type IN ('PERMIT - NEW CONSTRUCTION', 'PERMIT - RENOVATION/ALTERATION')) AS buildout,
          bool_or(a.t_electrical OR a.t_plumbing OR a.t_hvac) AS mep
        FROM fl f LEFT JOIN p a ON a.address_key = f.address_key AND a.issue_date > f.d
          AND a.issue_date <= f.d + INTERVAL 365 DAY
        WHERE f.d BETWEEN DATE '2016-01-01' AND DATE '2025-10-31'
        GROUP BY ALL
    """)
    groups = q(
        con,
        """
        SELECT CASE WHEN had_buildout THEN 'Build-out permit in prior 2 years' ELSE 'As-is takeover (no build-out permit in prior 2 years)' END AS grp,
          count(*) AS licenses,
          avg((first_permit IS NOT NULL)::INT) AS any_permit_rate,
          avg(coalesce(sign, false)::INT) AS sign_permit_rate,
          avg(coalesce(buildout, false)::INT) AS buildout_permit_rate,
          avg(coalesce(mep, false)::INT) AS mep_permit_rate,
          median(first_permit - d) AS median_days_to_first_permit
        FROM fl_x GROUP BY had_buildout ORDER BY had_buildout
    """,
    )
    asis = next(r for r in groups if r["grp"].startswith("As-is"))
    built = next(r for r in groups if r["grp"].startswith("Build-out"))
    vol = one(
        con,
        "SELECT count(*) FILTER (WHERE NOT had_buildout AND d > DATE '2025-10-31' - INTERVAL 365 DAY) / 52.0 AS v FROM fl_x",
    )["v"]
    return result(
        "H21",
        "New food license with no recent build-out permit (as-is takeover) → permits after opening",
        who="Signage, cleaning, security, small-trade contractors serving new restaurants",
        data="Retail food licenses, permits",
        signal="First food license for an account at an address, with no renovation/new-construction permit there in the prior 2 years",
        target="Any permit at the address within 365 days after the license",
        metrics=_round(
            {
                "groups": groups,
                "conversion": asis["any_permit_rate"],
                "baseline": built["any_permit_rate"],
                "signals_per_week": vol,
            }
        ),
        notes="Descriptive: compares as-is takeovers with licenses that followed a build-out. The food license "
        "table has no license type, so renewals under a new account number (ownership changes) look like new "
        "businesses. Address matching depends on a normalized street address; units in a building share one "
        "address, so a permit for another tenant counts. A first-year permit is not necessarily a build-out; the "
        "sign/MEP/build-out columns separate what kind of permit follows.",
    )


def h22_seasonality(con) -> dict:
    months = q(
        con,
        """
        WITH t AS (
          SELECT month(issue_date) AS m, count(*) AS n, count(*) FILTER (WHERE t_porch) AS porch,
            count(*) FILTER (WHERE t_masonry) AS masonry, count(*) FILTER (WHERE t_roofing) AS roofing
          FROM p WHERE issue_date BETWEEN DATE '2016-01-01' AND DATE '2025-12-31' GROUP BY 1
        )
        SELECT m AS month, porch / sum(porch) OVER () AS porch_share, masonry / sum(masonry) OVER () AS masonry_share,
          roofing / sum(roofing) OVER () AS roofing_share
        FROM t ORDER BY m
    """,
    )
    same_property(
        con,
        "SELECT address_key AS k, violation_date AS d FROM violations WHERE t_porch OR t_masonry",
        CHAIN_TARGET,
        365,
        "2016-01-01",
        "2025-10-31",
    )
    cited = q(
        con,
        """
        SELECT month(e.d) AS month, count(*) AS citations,
          avg((x.days IS NOT NULL)::INT) AS permit_within_365_share,
          median(x.days) AS median_days_citation_to_permit
        FROM ep e LEFT JOIN LATERAL (
          SELECT min(t.d - e.d) AS days FROM tgt t WHERE t.k = e.k AND t.d > e.d AND t.d <= e.d + INTERVAL 365 DAY
        ) x ON true
        GROUP BY 1 ORDER BY 1
    """,
    )
    by_month = {r["month"]: r for r in cited}
    rows = [{**r, **{k: v for k, v in by_month[r["month"]].items() if k != "month"}} for r in months]
    for r in rows:
        for k, v in r.items():
            if isinstance(v, float):
                r[k] = round(v, 4)
    return result(
        "H22",
        "Seasonality: when permits are pulled and how fast citations turn into permits, by month",
        who="Porch, masonry and roofing contractors (mailing calendar)",
        data="Permits (issue dates 2016-2025), building violations",
        signal="Calendar month of permit issue / of porch or masonry citation",
        target="Share of the year's porch, masonry and roofing permits; days from citation to permit",
        metrics={"groups": rows, "lift": None, "conversion": None, "baseline": None},
        notes="Descriptive. Permit shares are by issue month (when the job is cleared to start), which trails the "
        "decision by the permit-processing time; citation rows show, for citations issued in each month, how many "
        "got a porch/masonry permit within a year and the median days to it (only citations that converted, so "
        "the median is censored at 365). Weather, the City's inspection calendar and porch-season enforcement "
        "all move together here, so this is a calendar, not a causal effect of month.",
    )


# ----------------------------------------------------------------------------------------------------------
# Round 3: restaurant inspections as signals, matched against ordinary inspections
# ----------------------------------------------------------------------------------------------------------
VALID_RESULT = "results IN ('Pass', 'Pass w/ Conditions', 'Fail')"
INSPECTION_STRATA = """CASE
  WHEN inspection_type = 'License' THEN 'License (pre-opening)'
  WHEN lower(inspection_type) LIKE '%re-inspection%' THEN 'Re-inspection'
  WHEN inspection_type LIKE '%Complaint%' THEN 'Complaint'
  WHEN inspection_type = 'Canvass' THEN 'Canvass (routine)'
  ELSE 'Other' END"""
NAME_KEY = "regexp_replace(upper(coalesce({x}, '')), '[^A-Z0-9]', '', 'g')"
SAME_NAME = "(e.nm = t.nm OR (length(e.nm) >= 6 AND length(t.nm) >= 6 AND (contains(e.nm, t.nm) OR contains(t.nm, e.nm))))"


def inspection_vs_control(
    con,
    *,
    key: str,
    sig_where: str,
    ctl_where: str,
    target_sql: str,
    window: int,
    start: str,
    end: str,
    cond: str = "true",
    min_days: int = 0,
    obs_sql: str | None = None,
) -> dict:
    """Restaurant inspections that show a condition (signal) vs ordinary restaurant inspections without it.

    Both groups are one inspection per key per `window` days, and both must have no signal-type inspection in
    the previous `window` days. Control conversion is standardized to the signal group's inspection-type mix
    (a pre-opening 'License' inspection is a very different starting point from a routine canvass).
    target_sql -> (k, d, nm). cond may use e.nm / t.nm. min_days drops targets that follow too quickly.
    """
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE fi AS
        SELECT {key} AS k, inspection_date AS d, inspection_id, {INSPECTION_STRATA} AS strat, results,
          {NAME_KEY.format(x="dba")} AS nm, ({sig_where}) AS is_sig, ({ctl_where}) AS is_ctl
        FROM food_inspections WHERE facility_type = 'Restaurant' AND ({key}) IS NOT NULL
    """)
    con.execute(f"CREATE OR REPLACE TEMP TABLE tgt AS {target_sql}")
    con.execute("""
        CREATE OR REPLACE TEMP TABLE sig_all AS
        SELECT k, d, min(strat) AS strat, min(nm) AS nm, min(results) AS results FROM fi WHERE is_sig GROUP BY k, d
    """)
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE sig_ep AS
        SELECT k, d, strat, nm, results FROM (
          SELECT *, lag(d) OVER (PARTITION BY k ORDER BY d) AS prev FROM sig_all
        ) WHERE (prev IS NULL OR d - prev > {window}) AND d BETWEEN DATE '{start}' AND DATE '{end}'
    """)
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE ctl_ep AS
        SELECT k, d, strat, nm, results FROM (
          SELECT *, lag(d) OVER (PARTITION BY k ORDER BY d) AS prev FROM (
            SELECT c.k, c.d, min(c.strat) AS strat, min(c.nm) AS nm, min(c.results) AS results
            FROM fi c WHERE c.is_ctl AND NOT EXISTS (
              SELECT 1 FROM sig_all s WHERE s.k = c.k AND s.d > c.d - INTERVAL {window} DAY AND s.d <= c.d)
            GROUP BY c.k, c.d
          )
        ) WHERE (prev IS NULL OR d - prev > {window}) AND d BETWEEN DATE '{start}' AND DATE '{end}'
    """)
    if obs_sql:
        con.execute(f"CREATE OR REPLACE TEMP TABLE obs AS {obs_sql}")
        observed = f"EXISTS (SELECT 1 FROM obs o WHERE o.k = e.k AND o.d > e.d AND o.d <= e.d + INTERVAL {window} DAY)"
    else:
        observed = "NULL::BOOLEAN"
    for name in ("sig", "ctl"):
        con.execute(f"""
            CREATE OR REPLACE TEMP TABLE res_{name} AS
            SELECT e.k, e.d, e.strat, e.results,
              min(t.d - e.d) FILTER (WHERE t.d > e.d + INTERVAL {min_days} DAY
                AND t.d <= e.d + INTERVAL {window} DAY AND ({cond})) AS days,
              coalesce(bool_or(t.d > e.d - INTERVAL {2 * window} DAY AND t.d <= e.d - INTERVAL {window} DAY
                AND ({cond})), false) AS before,
              {observed} AS observed
            FROM {name}_ep e LEFT JOIN tgt t ON t.k = e.k
              AND t.d > e.d - INTERVAL {2 * window} DAY AND t.d <= e.d + INTERVAL {window} DAY
            GROUP BY e.k, e.d, e.strat, e.nm, e.results
        """)
    strata = q(
        con,
        """
        WITH s AS (SELECT strat, count(*) AS n, sum((days IS NOT NULL)::INT) AS hits,
                     sum(observed::INT) AS obs_n, sum((days IS NOT NULL AND observed)::INT) AS obs_hits
                   FROM res_sig GROUP BY 1),
        c AS (SELECT strat, count(*) AS n, sum((days IS NOT NULL)::INT) AS hits,
                     sum(observed::INT) AS obs_n, sum((days IS NOT NULL AND observed)::INT) AS obs_hits
                   FROM res_ctl GROUP BY 1)
        SELECT s.strat, s.n AS signals, s.hits AS signal_hits, c.n AS controls, c.hits AS control_hits,
          s.obs_n AS signal_observed, s.obs_hits AS signal_observed_hits,
          c.obs_n AS control_observed, c.obs_hits AS control_observed_hits
        FROM s LEFT JOIN c USING (strat) ORDER BY s.strat
    """,
    )
    tot = sum(r["signals"] for r in strata)
    usable = [r for r in strata if r["controls"]]
    wsum = sum(r["signals"] for r in usable)
    std = sum(r["signals"] / wsum * r["control_hits"] / r["controls"] for r in usable)
    sig_hits = sum(r["signal_hits"] for r in strata)
    cond_std = None
    sig_cond = None
    if obs_sql:
        ok = [r for r in usable if r["signal_observed"] and r["control_observed"]]
        w2 = sum(r["signal_observed"] for r in ok)
        cond_std = sum(
            r["signal_observed"] / w2 * r["control_observed_hits"] / r["control_observed"] for r in ok
        )
        sig_cond = sum(r["signal_observed_hits"] for r in ok) / w2
    raw_ctl = one(
        con,
        "SELECT avg((days IS NOT NULL)::INT) AS conv, avg((results = 'Fail')::INT) AS fail, count(*) AS n FROM res_ctl",
    )
    sg = one(
        con,
        """
        SELECT avg((days IS NOT NULL)::INT) AS conv, avg(before::INT) AS before, median(days) AS median_days,
          avg((results = 'Fail')::INT) AS fail, avg(observed::INT) AS observed,
          quantile_cont(days, 0.25) AS p25, quantile_cont(days, 0.75) AS p75,
          avg(coalesce(days > 30, false)::INT) AS after_30
        FROM res_sig
    """,
    )
    vol = one(
        con,
        "SELECT count(*) FILTER (WHERE d > (SELECT max(inspection_date) FROM food_inspections) - INTERVAL 365 DAY) / 52.0 AS v FROM sig_all",
    )["v"]
    by_year = q(
        con,
        """
        SELECT year(d) AS year, count(*) AS n, avg((days IS NOT NULL)::INT) AS conversion
        FROM res_sig GROUP BY 1 ORDER BY 1
    """,
    )
    ctl_year = {
        r["year"]: r["conversion"]
        for r in q(
            con, "SELECT year(d) AS year, avg((days IS NOT NULL)::INT) AS conversion FROM res_ctl GROUP BY 1"
        )
    }
    for r in by_year:
        r["control_conversion"] = ctl_year.get(r["year"])
    out = {
        "signals": tot,
        "conversion": sig_hits / tot,
        "baseline": std,
        "lift": sig_hits / tot / std if std else None,
        "raw_control_conversion": raw_ctl["conv"],
        "own_earlier_window": sg["before"],
        "median_days": sg["median_days"],
        "days_p25": sg["p25"],
        "days_p75": sg["p75"],
        "converted_after_30_days": sg["after_30"],
        "signals_per_week": vol,
        "signal_fail_share": sg["fail"],
        "control_fail_share": raw_ctl["fail"],
        "controls": raw_ctl["n"],
        "by_year": by_year,
        "strata": [
            {
                "strat": r["strat"],
                "signals": r["signals"],
                "signal_rate": r["signal_hits"] / r["signals"],
                "controls": r["controls"],
                "control_rate": (r["control_hits"] / r["controls"]) if r["controls"] else None,
            }
            for r in strata
        ],
    }
    if obs_sql:
        out.update(
            {
                "signal_reinspected_share": sg["observed"],
                "conversion_if_reinspected": sig_cond,
                "baseline_if_reinspected": cond_std,
                "lift_if_reinspected": sig_cond / cond_std if cond_std else None,
            }
        )
    return _round(out)


FI_START, FI_END_PERMIT = "2016-01-01", "2025-11-01"
FI_END_INSPECTION = "2026-05-01"


def h23_pest_persistence(con) -> dict:
    """Restaurant pest violation -> another pest violation at the same license within 180 days."""
    key = "nullif(license_no, 0)::VARCHAR"
    sig = f"f_pest AND {VALID_RESULT}"
    ctl = f"NOT f_pest AND {VALID_RESULT}"
    target = f"SELECT {key} AS k, inspection_date AS d, {NAME_KEY.format(x='dba')} AS nm FROM food_inspections WHERE f_pest AND {VALID_RESULT} AND license_no > 0 AND facility_type = 'Restaurant'"
    obs = f"SELECT {key} AS k, inspection_date AS d FROM food_inspections WHERE {VALID_RESULT} AND license_no > 0 AND facility_type = 'Restaurant'"
    kw = dict(
        key=key,
        sig_where=sig,
        ctl_where=ctl,
        target_sql=target,
        window=180,
        start="2016-07-01",
        end=FI_END_INSPECTION,
        obs_sql=obs,
    )
    m = inspection_vs_control(con, **kw)
    slow = inspection_vs_control(con, **kw, min_days=14)
    m["groups"] = [
        {
            "measure": "Any later pest violation within 180 days",
            "signal": m["conversion"],
            "matched_control": m["baseline"],
            "lift": m["lift"],
        },
        {
            "measure": "...only counting violations 15+ days later (not a quick re-check)",
            "signal": slow["conversion"],
            "matched_control": slow["baseline"],
            "lift": slow["lift"],
        },
        {
            "measure": "Any later pest violation, among restaurants re-inspected within 180 days",
            "signal": m["conversion_if_reinspected"],
            "matched_control": m["baseline_if_reinspected"],
            "lift": m["lift_if_reinspected"],
        },
        {
            "measure": "...among re-inspected, 15+ days later",
            "signal": slow["conversion_if_reinspected"],
            "matched_control": slow["baseline_if_reinspected"],
            "lift": slow["lift_if_reinspected"],
        },
        {
            "measure": "Share of the inspections that were a Fail",
            "signal": m["signal_fail_share"],
            "matched_control": m["control_fail_share"],
            "lift": m["signal_fail_share"] / m["control_fail_share"],
        },
        {
            "measure": "Share re-inspected within 180 days",
            "signal": m["signal_reinspected_share"],
            "matched_control": None,
            "lift": None,
        },
    ]
    # Headline = the most conservative view: recurrence 15+ days later among restaurants that were re-inspected,
    # so both groups had the same chance to be observed. The unconditional views reward the extra inspections
    # that follow a failure rather than a persistent problem.
    m["lift_any"] = m["lift"]
    m["lift_15plus_days"] = slow["lift"]
    m["conversion"] = slow["conversion_if_reinspected"]
    m["baseline"] = slow["baseline_if_reinspected"]
    m["lift"] = slow["lift_if_reinspected"]
    return result(
        "H23",
        "Restaurant pest violation → another pest violation within 180 days (recurring pest-control need)",
        who="Pest-control companies",
        data="Chicago food inspections (2016+, violation text flags)",
        signal="Restaurant inspection (Pass, Pass w/ Conditions or Fail) citing rodents, mice, roaches, insects, pests or droppings, with none at that license in the prior 180 days",
        target="Another pest violation at the same license 15 to 180 days later, among restaurants re-inspected in that window (headline); other views in the table",
        metrics=m,
        notes="'Conversion' is persistence of need (the restaurant still shows pests at a later inspection), not a purchase: "
        "nearly every restaurant is already required to keep pest control, so this identifies accounts with a "
        "problem, probably under contract with a competitor, and measures how long the need persists. The "
        "target can only be seen at a later inspection; failed restaurants are re-inspected quickly, which "
        "inflates the raw rate, so the control is ordinary inspections without pest violations (same license "
        "key, 180-day gap, inspection-type mix matched) and the table also shows 15+ day recurrence and rates among "
        "re-inspected restaurants. Violation text is classified by keywords (headings 'INSECTS, RODENTS & "
        "ANIMALS NOT PRESENT' and 'rodent proofed' count; the generic garbage-container heading does not). "
        "Weekly volume is episodes (first pest finding after 180 clean days) in the last 52 weeks of data.",
    )


def h24_plumbing_permit(con) -> dict:
    """Restaurant plumbing violation -> plumbing permit at the address within 365 days."""
    key = "address_key"
    target = "SELECT address_key AS k, issue_date AS d, '' AS nm FROM p WHERE t_plumbing AND address_key IS NOT NULL"
    base = dict(
        key=key,
        target_sql=target,
        window=365,
        start=FI_START,
        end=FI_END_PERMIT,
    )
    m = inspection_vs_control(
        con,
        sig_where=f"f_plumbing AND {VALID_RESULT}",
        ctl_where=f"NOT f_plumbing AND {VALID_RESULT}",
        **base,
    )
    strict = inspection_vs_control(
        con,
        sig_where=f"f_plumbing_strict AND {VALID_RESULT}",
        ctl_where=f"NOT f_plumbing_strict AND {VALID_RESULT}",
        **base,
    )
    fail = inspection_vs_control(
        con,
        sig_where="f_plumbing_strict AND results = 'Fail'",
        ctl_where=f"NOT f_plumbing_strict AND {VALID_RESULT}",
        **base,
    )
    m["groups"] = [
        {"definition": "Plumbing, leak, sewage, drain or hand-sink text", **_slim(m)},
        {"definition": "Strict: plumbing, leak, sewage, drain, backflow (no hand sinks)", **_slim(strict)},
        {"definition": "Strict and the inspection failed", **_slim(fail)},
    ]
    return result(
        "H24",
        "Restaurant plumbing violation → plumbing permit at the address within 365 days",
        who="Commercial plumbers, drain and grease-trap contractors",
        data="Chicago food inspections (2016+), permits",
        signal="Restaurant inspection citing plumbing, leaks, sewage, drains or hand sinks, none at that address in the prior 365 days",
        target="Plumbing permit (any permit tagged plumbing) at the same address within 365 days",
        metrics=m,
        notes="Matched control: ordinary restaurant inspections without a plumbing finding at the same kind of address "
        "(one per address per 365 days, inspection-type mix standardized). Permits are matched on street "
        "address, so a plumbing permit for another tenant or the landlord counts; the control has the same "
        "bias. Many fixes (faucets, traps, sinks) need no permit, so conversion is a floor. Hand-sink text is often "
        "about soap and towels rather than plumbing, hence the strict view. The headline is the broad flag.",
    )


def _slim(m: dict) -> dict:
    return {
        "signals": m["signals"],
        "conversion": m["conversion"],
        "matched_control": m["baseline"],
        "lift": m["lift"],
        "median_days": m["median_days"],
        "days_p25_p75": f"{m['days_p25']:.0f}-{m['days_p75']:.0f}" if m["days_p25"] is not None else None,
        "share_converting_after_30_days": m["converted_after_30_days"],
    }


def h25_hood_hvac_permit(con) -> dict:
    """Restaurant hood/ventilation violation -> HVAC or mechanical permit at the address within 365 days."""
    base = dict(key="address_key", window=365, start=FI_START, end=FI_END_PERMIT)
    hvac = (
        "SELECT address_key AS k, issue_date AS d, '' AS nm FROM p WHERE t_hvac AND address_key IS NOT NULL"
    )
    kitchen = (
        "SELECT address_key AS k, issue_date AS d, '' AS nm FROM p WHERE address_key IS NOT NULL AND "
        "regexp_matches(description, 'HOOD|EXHAUST|KITCHEN VENT|GREASE DUCT|MAKE-?UP AIR')"
    )
    m = inspection_vs_control(
        con,
        sig_where=f"f_hood AND {VALID_RESULT}",
        ctl_where=f"NOT f_hood AND {VALID_RESULT}",
        target_sql=hvac,
        **base,
    )
    broad = inspection_vs_control(
        con,
        sig_where=f"f_ventilation AND {VALID_RESULT}",
        ctl_where=f"NOT f_ventilation AND {VALID_RESULT}",
        target_sql=hvac,
        **base,
    )
    kit = inspection_vs_control(
        con,
        sig_where=f"f_hood AND {VALID_RESULT}",
        ctl_where=f"NOT f_hood AND {VALID_RESULT}",
        target_sql=kitchen,
        **base,
    )
    m["groups"] = [
        {"definition": "Hood, exhaust or duct text → HVAC/mechanical permit", **_slim(m)},
        {
            "definition": "Any ventilation heading (includes lighting) → HVAC/mechanical permit",
            **_slim(broad),
        },
        {"definition": "Hood, exhaust or duct text → hood/exhaust/kitchen-vent permit", **_slim(kit)},
    ]
    return result(
        "H25",
        "Restaurant hood/ventilation violation → HVAC or mechanical permit at the address within 365 days",
        who="Commercial HVAC, hood and exhaust-cleaning contractors",
        data="Chicago food inspections (2016+), permits",
        signal="Restaurant inspection citing a hood, exhaust or duct, none at that address in the prior 365 days",
        target="HVAC/mechanical permit (permits tagged hvac) at the same address within 365 days",
        metrics=m,
        notes="Hood cleaning and filter swaps need no permit, so only replacements and new installs appear. Permits "
        "are matched on street address (a building's other tenants and landlord count; the control has the same "
        "bias). The broad ventilation heading (#56 'ventilation & lighting' and the older '#38 ventilation') is "
        "shown separately because it also covers lighting.",
    )


def h26_out_of_business(con) -> dict:
    """Restaurant 'Out of Business' result -> new food license / renovation permit at the address."""
    base = dict(key="address_key", window=365, start=FI_START, end=FI_END_PERMIT)
    sig = "results = 'Out of Business'"
    ctl = VALID_RESULT
    new_license = (
        f"SELECT address_key AS k, issue_date AS d, {NAME_KEY.format(x='dba')} AS nm FROM food_licenses "
        "WHERE address_key IS NOT NULL AND issue_date IS NOT NULL"
    )
    reno = (
        "SELECT address_key AS k, issue_date AS d, '' AS nm FROM p WHERE address_key IS NOT NULL AND "
        "(permit_type = 'PERMIT - RENOVATION/ALTERATION' OR t_interior_buildout OR t_new_construction)"
    )
    lic = inspection_vs_control(
        con, sig_where=sig, ctl_where=ctl, target_sql=new_license, cond=f"NOT {SAME_NAME}", **base
    )
    lic_any = inspection_vs_control(con, sig_where=sig, ctl_where=ctl, target_sql=new_license, **base)
    lic_late = inspection_vs_control(
        con,
        sig_where=sig,
        ctl_where=ctl,
        target_sql=new_license,
        cond=f"NOT {SAME_NAME}",
        min_days=30,
        **base,
    )
    ren = inspection_vs_control(con, sig_where=sig, ctl_where=ctl, target_sql=reno, **base)
    m = lic
    m["groups"] = [
        {"definition": "New retail food license under a different business name (headline)", **_slim(lic)},
        {
            "definition": "New license (different name) issued 31+ days after the closure was recorded",
            **_slim(lic_late),
        },
        {"definition": "Any new retail food license, including the same name", **_slim(lic_any)},
        {"definition": "Renovation, build-out or new-construction permit", **_slim(ren)},
    ]
    return result(
        "H26",
        "Restaurant 'Out of Business' → new food license or renovation permit at the address within 365 days",
        who="Restaurant build-out contractors, equipment dealers, brokers, signage",
        data="Chicago food inspections (2016+), retail food licenses, permits",
        signal="Inspection result 'Out of Business' for a restaurant (first one at the address in 365 days)",
        target="New retail food license issued at the same address to a differently named business within 365 days; also a renovation/build-out/new-construction permit",
        metrics=m,
        notes="Space turnover. Control: ordinary restaurant inspections (Pass, Pass w/ Conditions, Fail) at an address, "
        "which also see turnover, so lift is the extra turnover after a closure. Closed spaces that re-let to a "
        "non-food tenant, or that reopen as the same name or a bar/cafe under another license class, are missed "
        "by the license test (the license table here is retail food establishments only), so conversion is a "
        "floor. Same-name matching drops ownership-transfer relicensing under the old trade name. The renovation "
        "permit view counts any renovation at the address, including unrelated tenants.",
    )


def h27_hmda_tracts(con) -> dict:
    """Home-improvement loans in a census tract in year Y vs residential permits per parcel in Y+1."""
    con.execute("INSTALL spatial; LOAD spatial;")
    con.execute("""
        CREATE OR REPLACE TEMP TABLE tg AS
        SELECT vintage, geoid, ST_GeomFromText(geom_wkt) AS geom FROM tracts
    """)
    con.execute("""
        CREATE OR REPLACE TEMP TABLE rp AS
        SELECT pin10, lat, lon FROM pin_pt WHERE pin10 IN (SELECT pin10 FROM resi)
    """)
    con.execute("""
        CREATE OR REPLACE TEMP TABLE rp_tract AS
        SELECT g.vintage, rp.pin10, g.geoid FROM rp JOIN tg g ON ST_Contains(g.geom, ST_Point(rp.lon, rp.lat))
    """)
    con.execute("""
        CREATE OR REPLACE TEMP TABLE tract_year AS
        WITH yrs AS (SELECT unnest(range(2018, 2026)) AS y),
        parcels_n AS (SELECT vintage, geoid, count(*) AS parcels FROM rp_tract GROUP BY ALL),
        loans AS (
          SELECT h.year AS y, h.tract AS geoid, count(*) AS loans FROM hmda_home_improvement h
          WHERE coalesce(h.business_purpose, '') <> '1' GROUP BY ALL
        ),
        permits_y AS (
          SELECT year(pp.issue_date) AS y, rt.vintage, rt.geoid, count(*) AS permits,
            count(DISTINCT pp.pin10) AS permitted_parcels
          FROM p pp JOIN rp_tract rt ON rt.pin10 = pp.pin10
          WHERE pp.permit_type NOT IN ('PERMIT - SIGNS', 'PERMIT - WRECKING/DEMOLITION')
            AND pp.issue_date BETWEEN DATE '2018-01-01' AND DATE '2025-12-31'
          GROUP BY ALL
        )
        SELECT yrs.y, n.vintage, n.geoid, n.parcels, coalesce(l.loans, 0) AS loans,
          coalesce(pm.permits, 0) AS permits, coalesce(pm.permitted_parcels, 0) AS permitted_parcels
        FROM yrs CROSS JOIN parcels_n n
        LEFT JOIN loans l ON l.y = yrs.y AND l.geoid = n.geoid
          AND n.vintage = CASE WHEN yrs.y <= 2021 THEN 2010 ELSE 2020 END
        LEFT JOIN permits_y pm ON pm.y = yrs.y AND pm.vintage = n.vintage AND pm.geoid = n.geoid
        WHERE n.parcels >= 100
    """)
    # Pair loan year Y with permits in Y+1 and the same tract's permits in Y (to see what the loans add).
    con.execute("""
        CREATE OR REPLACE TEMP TABLE pairs AS
        SELECT a.y AS loan_year, a.geoid, a.parcels, a.loans, 1000.0 * a.loans / a.parcels AS loan_rate,
          a.permitted_parcels AS permitted_now, b.permitted_parcels AS permitted_next,
          1.0 * a.permitted_parcels / a.parcels AS permit_rate_now,
          1.0 * b.permitted_parcels / b.parcels AS permit_rate_next
        FROM tract_year a JOIN tract_year b ON b.y = a.y + 1 AND b.geoid = a.geoid AND b.vintage = a.vintage
        WHERE a.vintage = CASE WHEN a.y <= 2021 THEN 2010 ELSE 2020 END
    """)
    con.execute("""
        CREATE OR REPLACE TEMP TABLE ranked AS
        WITH r AS (
          SELECT *,
            rank() OVER (PARTITION BY loan_year ORDER BY loan_rate) AS rk_x,
            count(*) OVER (PARTITION BY loan_year, loan_rate) AS ties_x,
            rank() OVER (PARTITION BY loan_year ORDER BY permit_rate_next) AS rk_y,
            count(*) OVER (PARTITION BY loan_year, permit_rate_next) AS ties_y,
            rank() OVER (PARTITION BY loan_year ORDER BY permit_rate_now) AS rk_z,
            count(*) OVER (PARTITION BY loan_year, permit_rate_now) AS ties_z,
            count(*) OVER (PARTITION BY loan_year) AS n
          FROM pairs
        )
        SELECT *, rk_x + (ties_x - 1) / 2.0 AS rx, rk_y + (ties_y - 1) / 2.0 AS ry, rk_z + (ties_z - 1) / 2.0 AS rz,
          floor(5 * (rk_x + (ties_x - 1) / 2.0 - 0.5) / n)::INT AS quintile
        FROM r
    """)
    years = q(
        con,
        """
        WITH c AS (
          SELECT loan_year, count(*) AS tracts, sum(loans) AS loans, corr(rx, ry) AS rho_loans_next,
            corr(rz, ry) AS rho_now_next, corr(rx, rz) AS rho_loans_now
          FROM ranked GROUP BY 1
        )
        SELECT loan_year, tracts, loans, rho_loans_next, rho_now_next, rho_loans_now,
          (rho_loans_next - rho_loans_now * rho_now_next)
            / sqrt((1 - rho_loans_now * rho_loans_now) * (1 - rho_now_next * rho_now_next)) AS partial_rho
        FROM c ORDER BY loan_year
    """,
    )
    quint = q(
        con,
        """
        SELECT quintile + 1 AS loan_quintile, count(*) AS tract_years, sum(parcels) AS parcels,
          sum(loans) AS loans, sum(permitted_next) AS permitted_parcels_next_year,
          sum(permitted_next) * 1.0 / sum(parcels) AS permit_rate_next_year,
          sum(permitted_now) * 1.0 / sum(parcels) AS permit_rate_same_year
        FROM ranked GROUP BY 1 ORDER BY 1
    """,
    )
    top, bottom = quint[-1], quint[0]
    n_years = len(years)
    metrics = {
        "conversion": top["permit_rate_next_year"],
        "baseline": bottom["permit_rate_next_year"],
        "lift": top["permit_rate_next_year"] / bottom["permit_rate_next_year"],
        "mean_rank_correlation": sum(r["rho_loans_next"] for r in years) / n_years,
        "mean_partial_rank_correlation": sum(r["partial_rho"] for r in years) / n_years,
        "mean_prior_permit_rank_correlation": sum(r["rho_now_next"] for r in years) / n_years,
        "years_tested": n_years,
        "signals_per_week": None,
        "by_year": years,
        "groups": quint,
    }
    # Top-quintile advantage that is left once the tract's own permit rate in the loan year is matched.
    top_quint_same_year = top["permit_rate_same_year"] / bottom["permit_rate_same_year"]
    metrics["same_year_lift"] = top_quint_same_year
    metrics["lift_beyond_prior_permits"] = (
        metrics["lift"] / top_quint_same_year if top_quint_same_year else None
    )
    return result(
        "H27",
        "Home-improvement mortgage loans per tract (HMDA, year Y) → residential permits per parcel (year Y+1)",
        who="All residential trades (neighborhood demand index for mail targeting)",
        data="CFPB HMDA home-improvement loans 2018-2025 (Cook County, loan years 2018-2024 paired with next-year permits, originated, loan_purpose=2), Chicago census tracts, Assessor parcels, permits",
        signal="Tract's home-improvement loans per 1,000 residential parcels in year Y (top quintile of Chicago tracts)",
        target="Share of the tract's residential parcels with any permit (excl. signs and demolition) in year Y+1 (top vs bottom loan quintile)",
        metrics=_round(metrics),
        notes="Area-level index, not a lead: HMDA covers only mortgage-financed work (about 2,000 Chicago loans a year, "
        "so most tracts have a handful), is reported on 2010 tracts through 2021 and 2020 tracts from 2022 (each "
        "year is matched to its own tract map), and wealthier, higher-equity neighborhoods have both more loans and "
        "more permits. Quintiles are drawn per loan year with ties kept together (the bottom quintile is mostly "
        "tracts with zero loans). The 2020 pairs overlap the pandemic. The lift is not controlled for income; "
        "compare it with same_year_lift (the same quintiles' permit rates in the loan year itself) and the "
        "partial rank correlation (rank correlation of loans with next-year permits once the tract's current permit rate "
        "is held fixed). Permits attach to parcels through PIN or address, so rates are floors.",
    )


def h28_radar_hail(con) -> dict:
    """Radar-detected hail cells (NEXRAD nx3hail) -> reroof permits on blocks under the swath."""
    lat_r, lon_r = 0.0225, 0.0302  # ~2.5 km
    lat_f, lon_f = 0.072, 0.0967  # ~8 km
    con.execute("""
        CREATE OR REPLACE TEMP TABLE hail_pts AS
        SELECT DISTINCT local_date AS d, round(lat, 3) AS lat, round(lon, 3) AS lon, max_size_in, sevprob
        FROM hail_cells WHERE lat BETWEEN 41.6 AND 42.1 AND lon BETWEEN -88.0 AND -87.45
    """)
    con.execute("CREATE OR REPLACE TEMP TABLE hcells AS SELECT DISTINCT cy, cx FROM resi")
    con.execute("""
        CREATE OR REPLACE TEMP TABLE rr AS
        SELECT r.cy, r.cx, p.issue_date FROM p JOIN resi r USING (pin10) WHERE p.t_roofing
    """)
    max_permit = one(con, "SELECT max(issue_date) AS d FROM permits")["d"]
    last_event = f"DATE '{max_permit}' - INTERVAL 125 DAY"

    def run(label: str, where: str, days: int = 120) -> dict:
        con.execute(f"""
            CREATE OR REPLACE TEMP TABLE hday AS
            SELECT d, lat, lon FROM hail_pts
            WHERE ({where}) AND d BETWEEN DATE '2016-03-01' AND {last_event} - INTERVAL {days - 120} DAY
        """)
        con.execute(f"""
            CREATE OR REPLACE TEMP TABLE near AS
            SELECT DISTINCT h.d, c.cy, c.cx FROM hday h JOIN hcells c
              ON abs(c.cy * {CELL_LAT} - h.lat) < {lat_r} AND abs(c.cx * {CELL_LON} - h.lon) < {lon_r}
        """)
        con.execute(f"""
            CREATE OR REPLACE TEMP TABLE touched AS
            SELECT DISTINCT a.d, c.cy, c.cx FROM hail_pts a JOIN hcells c
              ON a.d IN (SELECT d FROM hday)
              AND abs(c.cy * {CELL_LAT} - a.lat) < {lat_f} AND abs(c.cx * {CELL_LON} - a.lon) < {lon_f}
        """)
        con.execute("""
            CREATE OR REPLACE TEMP TABLE far AS
            SELECT d.d, c.cy, c.cx FROM (SELECT DISTINCT d FROM hday) d CROSS JOIN hcells c
            WHERE NOT EXISTS (SELECT 1 FROM touched t WHERE t.d = d.d AND t.cy = c.cy AND t.cx = c.cx)
        """)
        out = {}
        for name in ("near", "far"):
            out[name] = one(
                con,
                f"""
                SELECT count(*) AS cell_days,
                  count(DISTINCT x.d) AS event_days,
                  count(rr.issue_date) FILTER (WHERE rr.issue_date > x.d
                    AND rr.issue_date <= x.d + INTERVAL {days} DAY) AS after_n,
                  count(rr.issue_date) FILTER (WHERE rr.issue_date > x.d - INTERVAL 365 DAY
                    AND rr.issue_date <= x.d - INTERVAL {365 - days} DAY) AS year_before_n
                FROM {name} x LEFT JOIN rr ON rr.cy = x.cy AND rr.cx = x.cx
                  AND rr.issue_date > x.d - INTERVAL 365 DAY AND rr.issue_date <= x.d + INTERVAL {days} DAY
            """,
            )
        n, f = out["near"], out["far"]
        near_ratio = n["after_n"] / n["year_before_n"] if n["year_before_n"] else None
        far_ratio = f["after_n"] / f["year_before_n"] if f["year_before_n"] else None
        near_per_cell_day = n["after_n"] / n["cell_days"] if n["cell_days"] else None
        far_per_cell_day = f["after_n"] / f["cell_days"] if f["cell_days"] else None
        return {
            "definition": label,
            "event_days": n["event_days"],
            "near_cell_days": n["cell_days"],
            "near_after": n["after_n"],
            "near_year_before": n["year_before_n"],
            "far_after": f["after_n"],
            "far_year_before": f["year_before_n"],
            "near_ratio": near_ratio,
            "far_ratio": far_ratio,
            "lift": near_ratio / far_ratio if near_ratio and far_ratio else None,
            "raw_cell_day_ratio": near_per_cell_day / far_per_cell_day
            if near_per_cell_day and far_per_cell_day
            else None,
        }

    variants = [
        run("Radar hail cell of 1 inch or more within ~2.5 km (headline)", "max_size_in >= 1.0"),
        run("1 inch or more with severe-hail probability 30+", "max_size_in >= 1.0 AND sevprob >= 30"),
        run("1.75 inches (golf ball) or more", "max_size_in >= 1.75"),
        run(
            "1 inch or more, 270-day window (slower insurance-driven repairs)", "max_size_in >= 1.0", days=270
        ),
    ]
    head = variants[0]
    metrics = {
        "event_days": head["event_days"],
        "near_after": head["near_after"],
        "near_year_before": head["near_year_before"],
        "far_after": head["far_after"],
        "far_year_before": head["far_year_before"],
        "conversion": head["near_ratio"],
        "baseline": head["far_ratio"],
        "lift": head["lift"],
        "signals_per_week": head["event_days"] / (10.4 * 52),
        "groups": variants,
    }
    return result(
        "H28",
        "Radar-detected hail (NEXRAD) → reroof wave on blocks under the swath",
        who="Roofers, gutter and siding contractors, restoration",
        data="NOAA SWDI nx3hail radar hail detections 2016-2026 (Chicago area), permits",
        signal="NEXRAD hail detection of at least 1 inch within ~2.5 km of the block on the day (a centroid footprint, not a MESH grid)",
        target="Reroof permits on those blocks in the next 120 days (vs the same blocks a year earlier, vs blocks with no detection within ~8 km)",
        metrics=_round(metrics),
        notes="Retest of H04 with radar instead of spotter points. nx3hail gives one centroid per tracked hail cell per scan "
        "(probability, severe probability, estimated max size); a block counts as under the swath when a centroid "
        "of that size was within ~2.5 km that day, a stand-in for the true footprint (MESH grids would need "
        "GRIB processing). Day granularity is local time (UTC-6 approximation); detections only come from a box "
        "around the city, so blocks at its edge can be near storms we did not fetch. 'conversion' and 'baseline' "
        "are after/before permit ratios near and far; lift is their ratio. Insurance-paid repairs and "
        "unpermitted patching are invisible, so a null here is about permitted work only. Events from the last "
        "125 days of permit data are excluded so every window is complete.",
    )


# ----------------------------------------------------------------------------------------------------------
# Round 4: trades after a big permit, commercial reroof cycle model, business-license signals
# ----------------------------------------------------------------------------------------------------------
R4_START = "2016-01-01"
BUCKET_RESIDENTIAL = "single-family/other residential (2xx)"
BUCKET_UNKNOWN = "unknown class"


def class_bucket_sql(cls: str) -> str:
    return f"""CASE
      WHEN {cls} IS NULL THEN '{BUCKET_UNKNOWN}'
      WHEN left({cls}, 1) = '5' THEN 'commercial/industrial (5xx)'
      WHEN left({cls}, 1) = '3' THEN 'multifamily 7+ (3xx)'
      WHEN {cls} = '211' THEN '2-6 unit flats (211)'
      WHEN {cls} = '212' THEN 'mixed-use up to 6 units (212)'
      WHEN left({cls}, 1) = '2' THEN '{BUCKET_RESIDENTIAL}'
      WHEN left({cls}, 1) = '1' THEN 'vacant land (1xx)'
      ELSE 'exempt/other' END"""


def ensure_r4(con) -> None:
    """Temp tables shared by the round 4 hypotheses (idempotent): addr_map, pin_class, addr_cls, ctr."""
    if con.execute("SELECT count(*) FROM duckdb_tables() WHERE table_name = 'r4_ready'").fetchone()[0]:
        return
    con.execute("""
        CREATE OR REPLACE TEMP TABLE addr_map AS
        SELECT address_key, first(pin10 ORDER BY pri, pin10) AS pin10 FROM (
          SELECT address_key, pin10, 0 AS pri FROM addr_pin
          UNION ALL SELECT address_key, pin10, 1 FROM parcels WHERE address_key IS NOT NULL AND pin10 IS NOT NULL
        ) GROUP BY address_key
    """)
    con.execute("""
        CREATE OR REPLACE TEMP TABLE pin_class AS
        SELECT pin10, coalesce(rc.class, s.cls) AS cls FROM (
          SELECT pin10, first(class ORDER BY sale_date DESC, pin) AS cls FROM sales
          WHERE class IS NOT NULL GROUP BY pin10
        ) s FULL JOIN (SELECT pin10, class FROM res_chars) rc USING (pin10)
    """)
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE addr_cls AS
        SELECT m.address_key, m.pin10, c.cls, {class_bucket_sql("c.cls")} AS bucket
        FROM addr_map m LEFT JOIN pin_class c USING (pin10)
    """)
    con.execute("""
        CREATE OR REPLACE TEMP TABLE ctr AS
        SELECT DISTINCT permit_id, name_key FROM permit_parties
        WHERE name_key <> '' AND ((role NOT IN ('owner', 'owner_gc', 'architect', 'engineer', 'expediter', 'other'))
              OR role_raw LIKE '%CONTRACTOR%')
    """)
    con.execute("CREATE OR REPLACE TEMP TABLE r4_ready AS SELECT 1 AS x")


# --- H29 --------------------------------------------------------------------------------------------------
BIG_COST = 1_000_000
FOLLOW_WINDOW = 540
SCAFFOLD_LAST = "2023-11-17"  # the scaffolding permit type stops appearing in the feed after this date
OTHER_TYPES = "permit_type NOT IN ('PERMIT - SIGNS', 'PERMIT - ELEVATOR EQUIPMENT', 'PERMIT - SCAFFOLDING')"
FOLLOW_TRADES: dict[str, tuple[str, str]] = {
    "signs": ("permit_type = 'PERMIT - SIGNS'", "PERMIT - SIGNS"),
    "elevator": ("permit_type = 'PERMIT - ELEVATOR EQUIPMENT'", "PERMIT - ELEVATOR EQUIPMENT"),
    "electrical": (
        f"{OTHER_TYPES} AND t_electrical",
        "EXPRESS/EASY/RENOVATION text mentions electrical wiring",
    ),
    "scaffolding": ("permit_type = 'PERMIT - SCAFFOLDING'", "PERMIT - SCAFFOLDING (feed ends 2023-11-17)"),
    "plumbing": (f"{OTHER_TYPES} AND t_plumbing", "text mentions plumbing"),
    "hvac": (f"{OTHER_TYPES} AND t_hvac", "text mentions mechanical/HVAC"),
    "fire_alarm": (f"{OTHER_TYPES} AND t_fire_alarm", "text mentions fire alarm/sprinkler"),
    "roofing": (f"{OTHER_TYPES} AND t_roofing", "text mentions roofing"),
    "demolition": ("permit_type = 'PERMIT - WRECKING/DEMOLITION'", "PERMIT - WRECKING/DEMOLITION"),
    "renovation": (
        "permit_type = 'PERMIT - RENOVATION/ALTERATION' OR t_interior_buildout",
        "PERMIT - RENOVATION/ALTERATION or interior build-out text",
    ),
}
HEADLINE_TRADES = ("signs", "elevator", "electrical")
H29_BUCKETS = (
    "commercial/industrial (5xx)",
    "multifamily 7+ (3xx)",
    "mixed-use up to 6 units (212)",
    "2-6 unit flats (211)",
    "exempt/other",
)


def _quartiles(vals_sql_col: str) -> str:
    return (
        f"median({vals_sql_col}) AS med, quantile_cont({vals_sql_col}, 0.25) AS p25, "
        f"quantile_cont({vals_sql_col}, 0.75) AS p75"
    )


def h29_trades_after_big_permit(con) -> dict:
    """Major commercial/multifamily permit at an address -> which follow-on permits come, and are the people
    on them already named on the big permit."""
    ensure_r4(con)
    max_issue = one(con, "SELECT max(issue_date) AS d FROM permits")["d"]
    end = f"DATE '{max_issue}' - INTERVAL {FOLLOW_WINDOW} DAY"
    flag_cols = ", ".join(f"({pred}) AS f_{name}" for name, (pred, _) in FOLLOW_TRADES.items())
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE fo AS
        SELECT id, address_key AS k, issue_date AS d, {flag_cols} FROM p WHERE address_key IS NOT NULL
    """)
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE maj_all AS
        SELECT id, address_key AS k, issue_date AS d, address_key || '@' || issue_date::VARCHAR AS sk,
          reported_cost AS cost, pin10 FROM p
        WHERE permit_type IN ('PERMIT - NEW CONSTRUCTION', 'PERMIT - RENOVATION/ALTERATION')
          AND reported_cost >= {BIG_COST} AND address_key IS NOT NULL
    """)
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE sig AS
        SELECT sk, k, d, cost, bucket FROM (
          SELECT sk, k, d, cost, {class_bucket_sql("pc.cls")} AS bucket,
            lag(d) OVER (PARTITION BY k ORDER BY d) AS prev
          FROM (SELECT sk, k, d, max(cost) AS cost, first(pin10 ORDER BY cost DESC, id) AS pin10
                FROM maj_all GROUP BY sk, k, d) m
          LEFT JOIN pin_class pc USING (pin10)
        ) WHERE (prev IS NULL OR d - prev > {FOLLOW_WINDOW}) AND d >= DATE '{R4_START}'
    """)
    con.execute("""
        CREATE OR REPLACE TEMP TABLE mpp AS
        SELECT DISTINCT m.sk, c.name_key FROM maj_all m JOIN ctr c ON c.permit_id = m.id
    """)
    flags = ", ".join(f"t.f_{n}" for n in FOLLOW_TRADES)
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE pr AS
        SELECT s.sk, s.d AS sd, s.bucket, t.id AS tid, t.d - s.d AS days, {flags},
          EXISTS (SELECT 1 FROM ctr c WHERE c.permit_id = t.id) AS named
        FROM sig s JOIN fo t ON t.k = s.k AND t.d > s.d AND t.d <= s.d + INTERVAL {FOLLOW_WINDOW} DAY
    """)
    con.execute("""
        CREATE OR REPLACE TEMP TABLE lk AS
        SELECT DISTINCT pr.sk, pr.tid FROM pr JOIN ctr c ON c.permit_id = pr.tid
        JOIN mpp m ON m.name_key = c.name_key AND m.sk = pr.sk
    """)
    con.execute("""
        CREATE OR REPLACE TEMP TABLE pr2 AS
        SELECT pr.*, (lk.tid IS NOT NULL) AS locked FROM pr LEFT JOIN lk USING (sk, tid)
    """)
    # control pools: quarterly address-quarters without a major permit within +-540 days
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE qd AS
        SELECT unnest(generate_series(DATE '{R4_START}', {end}, INTERVAL 3 MONTH))::DATE AS q
    """)
    bucket_list = ", ".join(f"'{b}'" for b in H29_BUCKETS)
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE pool_a AS
        SELECT a.address_key AS k, qd.q, a.bucket FROM (SELECT DISTINCT address_key, bucket FROM addr_cls
          WHERE bucket IN ({bucket_list})) a CROSS JOIN qd
        WHERE NOT EXISTS (SELECT 1 FROM maj_all m WHERE m.k = a.address_key
          AND m.d > qd.q - INTERVAL {FOLLOW_WINDOW} DAY AND m.d <= qd.q + INTERVAL {FOLLOW_WINDOW} DAY)
    """)
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE pool_b AS
        SELECT DISTINCT a.k, a.q, a.bucket FROM (
          SELECT p2.address_key AS k, qd.q, ac.bucket FROM p p2 CROSS JOIN qd
          JOIN (SELECT DISTINCT address_key, bucket FROM addr_cls WHERE bucket IN ({bucket_list})) ac
            ON ac.address_key = p2.address_key
          WHERE p2.permit_type IN ('PERMIT - NEW CONSTRUCTION', 'PERMIT - RENOVATION/ALTERATION')
            AND p2.reported_cost >= 100000 AND p2.reported_cost < {BIG_COST}
            AND p2.issue_date > qd.q - INTERVAL 90 DAY AND p2.issue_date <= qd.q
        ) a
        WHERE NOT EXISTS (SELECT 1 FROM maj_all m WHERE m.k = a.k
          AND m.d > a.q - INTERVAL {FOLLOW_WINDOW} DAY AND m.d <= a.q + INTERVAL {FOLLOW_WINDOW} DAY)
    """)
    for pool in ("a", "b"):
        con.execute(f"""
            CREATE OR REPLACE TEMP TABLE hit_{pool} AS
            SELECT c.k, c.q, {", ".join(f"bool_or(t.f_{n}) AS f_{n}" for n in FOLLOW_TRADES)}
            FROM pool_{pool} c JOIN fo t ON t.k = c.k AND t.d > c.q AND t.d <= c.q + INTERVAL {FOLLOW_WINDOW} DAY
            GROUP BY c.k, c.q
        """)

    def cohort_end(trade: str | None) -> str:
        if trade == "scaffolding":
            return f"least({end}, DATE '{SCAFFOLD_LAST}' - INTERVAL {FOLLOW_WINDOW} DAY)"
        return end

    def std_rate(pool: str, flag_expr: str, weights: dict[str, float], e: str) -> float:
        rows = q(
            con,
            f"""
            SELECT c.bucket, count(*) AS n, count(*) FILTER (WHERE {flag_expr}) AS hits
            FROM pool_{pool} c LEFT JOIN hit_{pool} h ON h.k = c.k AND h.q = c.q
            WHERE c.q <= {e} GROUP BY 1
        """,
        )
        by = {r["bucket"]: r for r in rows}
        tot = sum(w for b, w in weights.items() if b in by and by[b]["n"])
        return sum(w / tot * by[b]["hits"] / by[b]["n"] for b, w in weights.items() if b in by and by[b]["n"])

    def trade_stats(name: str, any_of: tuple[str, ...]) -> dict:
        e = cohort_end(name if name == "scaffolding" else None)
        sflag = " OR ".join(f"r.f_{n}" for n in any_of)
        hflag = " OR ".join(f"h.f_{n}" for n in any_of)
        sig_rows = q(
            con,
            f"""
            WITH s AS (SELECT * FROM sig WHERE d <= {e} AND bucket IN ({bucket_list})),
            per AS (
              SELECT s.sk, s.bucket, min(r.days) FILTER (WHERE {sflag}) AS first_days,
                bool_or(({sflag}) AND r.named AND NOT r.locked) AS has_new,
                bool_or(({sflag}) AND r.named AND r.locked) AS has_locked,
                bool_or(({sflag}) AND NOT r.named) AS has_unnamed,
                EXISTS (SELECT 1 FROM fo x WHERE x.k = s.k AND ({" OR ".join(f"x.f_{n}" for n in any_of)})
                  AND x.d > s.d - INTERVAL {2 * FOLLOW_WINDOW} DAY AND x.d <= s.d - INTERVAL {FOLLOW_WINDOW} DAY)
                  AS before
              FROM s LEFT JOIN pr2 r ON r.sk = s.sk GROUP BY s.sk, s.k, s.d, s.bucket
            )
            SELECT bucket, count(*) AS n, count(first_days) AS hits, sum(coalesce(has_new, false)::INT) AS new_hits,
              sum(coalesce(has_locked, false)::INT) AS locked_hits, sum(coalesce(has_unnamed, false)::INT) AS unnamed_hits,
              sum(before::INT) AS before_hits
            FROM per GROUP BY bucket ORDER BY bucket
        """,
        )
        n = sum(r["n"] for r in sig_rows)
        hits = sum(r["hits"] for r in sig_rows)
        weights = {r["bucket"]: r["n"] / n for r in sig_rows}
        base_a = std_rate("a", hflag, weights, e)
        base_b = std_rate("b", hflag, weights, e)
        t = one(
            con,
            f"""
            SELECT count(*) AS n, count(*) FILTER (WHERE named) AS named_n,
              count(*) FILTER (WHERE named AND locked) AS locked_n,
              count(*) FILTER (WHERE named AND NOT locked) AS new_n
            FROM pr2 r WHERE r.sd <= {e} AND r.bucket IN ({bucket_list}) AND ({sflag})
        """,
        )
        tm = one(
            con,
            f"""
            WITH s AS (SELECT * FROM sig WHERE d <= {e} AND bucket IN ({bucket_list})),
            per AS (SELECT s.sk, min(r.days) AS first_days FROM s JOIN pr2 r ON r.sk = s.sk AND ({sflag}) GROUP BY s.sk)
            SELECT {_quartiles("first_days")} FROM per
        """,
        )
        return {
            "signals": n,
            "followon_rate": hits / n,
            "own_earlier_rate": sum(r["before_hits"] for r in sig_rows) / n,
            "lift_vs_own": hits / n / (sum(r["before_hits"] for r in sig_rows) / n)
            if sum(r["before_hits"] for r in sig_rows)
            else None,
            "matched_control_rate": base_a,
            "lift_vs_matched": hits / n / base_a if base_a else None,
            "busy_control_rate": base_b,
            "lift_vs_busy": hits / n / base_b if base_b else None,
            "median_days": tm["med"],
            "p25_days": tm["p25"],
            "p75_days": tm["p75"],
            "new_contractor_rate": sum(r["new_hits"] for r in sig_rows) / n,
            "locked_in_rate": sum(r["locked_hits"] for r in sig_rows) / n,
            "permits": t["n"],
            "new_share": t["new_n"] / t["n"] if t["n"] else None,
            "locked_share": t["locked_n"] / t["n"] if t["n"] else None,
            "unnamed_share": (t["n"] - t["named_n"]) / t["n"] if t["n"] else None,
            "_by_bucket": sig_rows,
            "_weights": weights,
        }

    by_trade = []
    stats: dict[str, dict] = {}
    for name in FOLLOW_TRADES:
        st = trade_stats(name, (name,))
        stats[name] = st
        by_trade.append(
            {"trade": name, "permit_types": FOLLOW_TRADES[name][1]}
            | {k: v for k, v in st.items() if not k.startswith("_")}
        )
    head = trade_stats("headline", HEADLINE_TRADES)
    by_class = []
    for r in head["_by_bucket"]:
        e = end
        w = {r["bucket"]: 1.0}
        base_a = std_rate("a", " OR ".join(f"h.f_{n}" for n in HEADLINE_TRADES), w, e)
        by_class.append(
            {
                "class": r["bucket"],
                "signals": r["n"],
                "followon_rate": r["hits"] / r["n"],
                "matched_control_rate": base_a,
                "lift_vs_matched": r["hits"] / r["n"] / base_a if base_a else None,
            }
        )
    unknown = one(
        con,
        f"""
        SELECT count(*) AS n, avg((EXISTS (SELECT 1 FROM pr2 r WHERE r.sk = s.sk
          AND (r.f_signs OR r.f_elevator OR r.f_electrical)))::INT) AS rate
        FROM sig s WHERE s.d <= {end} AND s.bucket NOT IN ({bucket_list})
    """,
    )
    by_year = q(
        con,
        f"""
        SELECT year(s.d) AS year, count(*) AS n,
          avg((EXISTS (SELECT 1 FROM pr2 r WHERE r.sk = s.sk
            AND (r.f_signs OR r.f_elevator OR r.f_electrical)))::INT) AS conversion
        FROM sig s WHERE s.d <= {end} AND s.bucket IN ({bucket_list}) GROUP BY 1 ORDER BY 1
    """,
    )
    vol = one(
        con,
        f"""
        SELECT count(*) FILTER (WHERE bucket NOT IN ('{BUCKET_RESIDENTIAL}', 'vacant land (1xx)')) / 52.0 AS v,
          count(*) FILTER (WHERE bucket IN ({bucket_list})) / 52.0 AS v_known
        FROM sig WHERE d > DATE '{max_issue}' - INTERVAL 365 DAY
    """,
    )
    own = head["own_earlier_rate"]
    metrics = _round_deep(
        {
            "signals": head["signals"],
            "conversion": head["followon_rate"],
            "baseline": own,
            "lift": head["lift_vs_own"],
            "matched_control_rate": head["matched_control_rate"],
            "lift_vs_matched_control": head["lift_vs_matched"],
            "busy_control_rate": head["busy_control_rate"],
            "lift_vs_busy": head["lift_vs_busy"],
            "signals_per_week_class_known": vol["v_known"],
            "median_days": head["median_days"],
            "days_p25": head["p25_days"],
            "days_p75": head["p75_days"],
            "signals_per_week": vol["v"],
            "unknown_class_signals": unknown["n"],
            "unknown_class_followon_rate": unknown["rate"],
            "by_trade": by_trade,
            "by_class": by_class,
            "by_year": by_year,
        }
    )
    return result(
        "H29",
        "Which trades are still open after a $1M+ commercial/multifamily permit (signs, elevator, electrical, ...)",
        who="Sign shops, elevator service, electricians and other trade subcontractors; suppliers selling to them",
        data="Permits (types: NEW CONSTRUCTION, RENOVATION/ALTERATION, SIGNS, ELEVATOR EQUIPMENT, SCAFFOLDING, "
        "WRECKING/DEMOLITION, EXPRESS PERMIT PROGRAM, EASY PERMIT PROCESS), permit parties, parcel classes from sales",
        signal=f"New-construction or renovation/alteration permit with reported cost of at least ${BIG_COST:,} at an "
        "address whose parcel class is commercial/industrial, 7+ unit multifamily, mixed-use, 2-6 flats or exempt "
        "(first one at the address in 540 days)",
        target="A follow-on permit at the same address within 540 days for a sign, an elevator or electrical work "
        "(headline; other trades in the table), and whether its contractor was already named on the big permit",
        metrics=metrics,
        notes="Class comes from the latest Cook County sale or the residential characteristics file, so addresses "
        "with no sale since 2010 have no class (reported separately, no matched control). 'matched_control_rate' = "
        "same-window rate at addresses of the same class bucket with no major permit within +-540 days, "
        "standardized to the signals' class mix; 'busy_control_rate' = same for addresses with a $100k-$1M "
        "renovation/new-construction permit in the prior 90 days and no major permit; 'own_earlier_rate' = the same "
        "address in the window 540-1,080 days before. The feed has no 'electric wiring' permit type: electrical, "
        "plumbing, HVAC, fire-alarm and roofing follow-ons are permits (express/easy/renovation) whose text names "
        "that work. 'locked in' = a contractor on the follow-on permit has the same normalized name as a contractor on "
        "any big permit at that address that day (names are cut at 30 characters, so variants count as new); "
        "'unnamed' = no contractor on the follow-on permit; shares are per permit, rates are per signal. Follow-ons "
        "issued the same day as the big permit are excluded. The scaffolding permit type disappears from the feed "
        "after 2023-11-17, so its cohort ends 540 days before that. Permits capture permitted work only.",
    )


# --- H30 --------------------------------------------------------------------------------------------------
ASOF_START, ASOF_END = "2016-01-01", "2023-10-01"
TRAIN_END, TEST_START, TEST_END = "2019-12-31", "2021-01-01", "2023-12-31"
VAL_FIT_END, VAL_START, VAL_END = "2017-01-01", "2018-01-01", "2019-10-01"
MODEL_FEATURES = ("roof", "cls", "age", "viol", "hail")  # back-off order: the last one is dropped first
FEATURE_LABELS = {
    "roof": "years since last roof permit",
    "cls": "class code",
    "age": "building age",
    "viol": "roofing violation in prior 2 years",
    "hail": "hail detection within ~1 km in prior 3 years",
}
RATE_SHRINK = 100  # pseudo-observations at the base rate, as in signals.fit_combo_rates
MIN_N_GRID = (300, 1000, 3000)
HAIL_LAT, HAIL_LON = 0.009, 0.0121  # ~1 km


def _build_h30_matrix(con) -> None:
    """Temp table m30: one row per (segment, as-of date, parcel) with bucketed features and the target y."""
    ensure_r4(con)
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE asof30 AS
        SELECT unnest(generate_series(DATE '{ASOF_START}', DATE '{ASOF_END}', INTERVAL 3 MONTH))::DATE AS d
    """)
    con.execute("""
        CREATE OR REPLACE TEMP TABLE roofs30 AS
        SELECT DISTINCT pin10, issue_date FROM p WHERE t_roofing AND pin10 IS NOT NULL
    """)
    con.execute("""
        CREATE OR REPLACE TEMP TABLE vroof30 AS
        SELECT DISTINCT m.pin10, v.violation_date FROM violations v JOIN addr_map m USING (address_key)
        WHERE v.t_roofing AND v.violation_date IS NOT NULL
    """)
    con.execute("""
        CREATE OR REPLACE TEMP TABLE sale_cls AS
        SELECT pin10, sale_date, first(class ORDER BY pin) AS cls FROM sales
        WHERE sale_date IS NOT NULL AND class IS NOT NULL
          AND pin10 IN (SELECT pin10 FROM sales WHERE left(class, 1) IN ('3', '5'))
        GROUP BY pin10, sale_date
    """)
    con.execute("""
        CREATE OR REPLACE TEMP TABLE uni30 AS
        SELECT 'main' AS seg, a.d, a.pin10, s.cls FROM (
          SELECT d, pin10 FROM asof30 CROSS JOIN (SELECT DISTINCT pin10 FROM sale_cls) x
        ) a ASOF JOIN sale_cls s ON a.pin10 = s.pin10 AND a.d >= s.sale_date
        WHERE left(s.cls, 1) IN ('3', '5')
        UNION ALL
        SELECT 'flats', d, pin10, class FROM asof30 CROSS JOIN res_chars WHERE class IN ('211', '212')
    """)
    con.execute("""
        CREATE OR REPLACE TEMP TABLE yb30 AS
        SELECT pin10, min(yb) AS yb FROM (
          SELECT pin10, year_built AS yb FROM res_chars
          UNION ALL SELECT m.pin10, b.year_built FROM benchmarking b JOIN addr_map m USING (address_key)
        ) WHERE yb BETWEEN 1800 AND 2026 GROUP BY pin10
    """)
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE pt30 AS
        SELECT m.pin10, median(b.lat) AS lat, median(b.lon) AS lon FROM addr_map m JOIN (
          SELECT address_key, lat, lon FROM (
            SELECT address_key, lat, lon, issue_date AS dt FROM permits
            UNION ALL SELECT address_key, lat, lon, violation_date FROM violations
            UNION ALL SELECT address_key, lat, lon, created_date FROM sr311
            UNION ALL SELECT address_key, lat, lon, issue_date FROM biz_license_history
          ) WHERE dt < DATE '{ASOF_START}' AND lat BETWEEN 41.6 AND 42.1 AND lon BETWEEN -87.95 AND -87.5
            AND address_key IS NOT NULL
        ) b USING (address_key)
        WHERE m.pin10 IN (SELECT DISTINCT pin10 FROM uni30)
        GROUP BY m.pin10
    """)
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE parcel_hail AS
        SELECT DISTINCT pt.pin10, h.local_date AS hd FROM pt30 pt JOIN (
          SELECT DISTINCT local_date, lat, lon FROM hail_cells WHERE max_size_in >= 1.0
        ) h ON abs(pt.lat - h.lat) <= {HAIL_LAT} AND abs(pt.lon - h.lon) <= {HAIL_LON}
    """)
    con.execute("""
        CREATE OR REPLACE TEMP TABLE hail30 AS
        SELECT u.d, u.pin10, count(DISTINCT ph.hd) AS n_days FROM uni30 u
        JOIN parcel_hail ph ON ph.pin10 = u.pin10 AND ph.hd > u.d - INTERVAL 3 YEAR AND ph.hd <= u.d
        GROUP BY u.d, u.pin10
    """)
    con.execute("""
        CREATE OR REPLACE TEMP TABLE yhit30 AS
        SELECT DISTINCT u.d, u.pin10 FROM uni30 u JOIN roofs30 r ON r.pin10 = u.pin10
          AND r.issue_date > u.d AND r.issue_date <= u.d + INTERVAL 365 DAY
    """)
    con.execute("""
        CREATE OR REPLACE TEMP TABLE codes30 AS
        SELECT cls, count(DISTINCT pin10) AS pins FROM uni30 GROUP BY cls
    """)
    con.execute("""
        CREATE OR REPLACE TEMP TABLE m30 AS
        SELECT u.seg, u.d, u.pin10,
          CASE WHEN r.issue_date IS NULL THEN 'none on record'
               WHEN u.d - r.issue_date < 1095 THEN '<3y'
               WHEN u.d - r.issue_date < 2555 THEN '3-7y'
               WHEN u.d - r.issue_date < 4380 THEN '7-12y' ELSE '12y+' END AS roof,
          CASE WHEN c.pins >= 300 THEN u.cls WHEN left(u.cls, 1) = '5' THEN 'other 5xx' ELSE 'other 3xx' END AS cls,
          CASE WHEN y.yb IS NULL OR y.yb > year(u.d) THEN 'unknown'
               WHEN year(u.d) - y.yb < 20 THEN '<20y' WHEN year(u.d) - y.yb < 50 THEN '20-50y'
               WHEN year(u.d) - y.yb < 80 THEN '50-80y' ELSE '80y+' END AS age,
          CASE WHEN v.violation_date IS NOT NULL AND u.d - v.violation_date <= 730 THEN 'yes' ELSE 'no' END AS viol,
          CASE WHEN pt.pin10 IS NULL THEN 'no location' WHEN coalesce(h.n_days, 0) = 0 THEN '0'
               WHEN h.n_days = 1 THEN '1' ELSE '2+' END AS hail,
          CASE WHEN coalesce(h.n_days, 0) = 0 THEN '0' WHEN h.n_days = 1 THEN '1' ELSE '2+' END AS hail_only,
          (yh.pin10 IS NOT NULL) AS y
        FROM uni30 u
        ASOF LEFT JOIN roofs30 r ON u.pin10 = r.pin10 AND u.d >= r.issue_date
        ASOF LEFT JOIN vroof30 v ON u.pin10 = v.pin10 AND u.d >= v.violation_date
        LEFT JOIN codes30 c ON c.cls = u.cls
        LEFT JOIN yb30 y ON y.pin10 = u.pin10
        LEFT JOIN pt30 pt ON pt.pin10 = u.pin10
        LEFT JOIN hail30 h ON h.d = u.d AND h.pin10 = u.pin10
        LEFT JOIN yhit30 yh ON yh.d = u.d AND yh.pin10 = u.pin10
    """)


def _fit_predict(con, seg: str, feats: tuple[str, ...], fit_where: str, apply_where: str, min_n: int) -> None:
    """Temp table pred30(d, pin10, y, p): back-off rate table fitted on `fit_where`, applied to `apply_where`."""
    base = one(con, f"SELECT avg(y::INT) AS r FROM m30 WHERE seg = '{seg}' AND {fit_where}")["r"]
    lv_sql = []
    for i, k in enumerate(range(len(feats), 0, -1)):
        cols = ", ".join(feats[:k])
        con.execute(f"""
            CREATE OR REPLACE TEMP TABLE lv30_{i} AS
            SELECT {cols}, count(*) AS n, (sum(y::INT) + {RATE_SHRINK} * {base}) / (count(*) + {RATE_SHRINK}) AS rate
            FROM m30 WHERE seg = '{seg}' AND {fit_where} GROUP BY ALL
        """)
        on = " AND ".join(f"m.{c} = l{i}.{c}" for c in feats[:k])
        lv_sql.append((i, on))
    joins = " ".join(f"LEFT JOIN lv30_{i} l{i} ON {on}" for i, on in lv_sql)
    cases = ", ".join(f"CASE WHEN l{i}.n >= {min_n} THEN l{i}.rate END" for i, _ in lv_sql)
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE pred30 AS
        SELECT m.d, m.pin10, m.y, coalesce({cases + ", " if cases else ""}{base}) AS p
        FROM m30 m {joins} WHERE m.seg = '{seg}' AND {apply_where}
    """)


def _wilson(hits: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if not n:
        return (0.0, 0.0)
    ph = hits / n
    den = 1 + z * z / n
    centre = (ph + z * z / (2 * n)) / den
    half = z * ((ph * (1 - ph) / n + z * z / (4 * n * n)) ** 0.5) / den
    return (centre - half, centre + half)


def _evaluate_pred(con, ks: tuple[int, ...] = (100, 1000)) -> dict:
    """Metrics for pred30: precision@K per as-of date (pooled over dates), capture in the top 10%, log-loss skill."""
    sums = ", ".join(
        f"sum(y::INT) FILTER (WHERE rn <= {k}) AS h{k}, count(*) FILTER (WHERE rn <= {k}) AS n{k}" for k in ks
    )
    r = one(
        con,
        f"""
        WITH r AS (
          SELECT d, y, p, row_number() OVER (PARTITION BY d ORDER BY p DESC, hash(pin10 || d::VARCHAR), pin10) AS rn,
            count(*) OVER (PARTITION BY d) AS cnt FROM pred30
        )
        SELECT count(*) AS rows, sum(y::INT) AS hits, count(DISTINCT d) AS dates, {sums},
          sum(y::INT) FILTER (WHERE rn <= cnt * 0.1) AS top10_hits,
          avg(-(y::INT * ln(least(greatest(p, 1e-6), 1 - 1e-6))
                + (1 - y::INT) * ln(1 - least(greatest(p, 1e-6), 1 - 1e-6)))) AS log_loss
        FROM r
    """,
    )
    base = r["hits"] / r["rows"]
    ll_base = -(base * math.log(base) + (1 - base) * math.log(1 - base))
    out = {"rows": r["rows"], "base_rate": base}
    for k in ks:
        prec = r[f"h{k}"] / r[f"n{k}"]
        lo, hi = _wilson(r[f"h{k}"], r[f"n{k}"])
        out[f"p_at_{k}_rate"] = prec
        out[f"hits_at_{k}"] = r[f"h{k}"]
        out[f"lift_at_{k}"] = prec / base if base else None
        out[f"p_at_{k}_low_rate"] = lo
        out[f"p_at_{k}_high_rate"] = hi
    out["top10_capture_share"] = r["top10_hits"] / r["hits"] if r["hits"] else None
    out["log_loss_skill_share"] = 1 - r["log_loss"] / ll_base
    return out


def _calibration(con) -> list[dict]:
    return q(
        con,
        """
        WITH r AS (
          SELECT y, p, ntile(10) OVER (ORDER BY p, hash(pin10 || d::VARCHAR), pin10, d) AS decile FROM pred30
        )
        SELECT decile, count(*) AS rows, avg(p) AS predicted_rate, avg(y::INT) AS observed_rate, sum(y::INT) AS hits
        FROM r GROUP BY decile ORDER BY decile
    """,
    )


def _h30_segment(con, seg: str, min_n: int) -> dict:
    full = MODEL_FEATURES
    test = f"d >= DATE '{TEST_START}' AND d <= DATE '{TEST_END}'"
    fit = f"d <= DATE '{TRAIN_END}'"
    variants: list[tuple[str, tuple[str, ...]]] = [
        ("full model", full),
        ("years since last roof permit only", ("roof",)),
        ("building age only", ("age",)),
        ("class code only", ("cls",)),
    ]
    rows = []
    for name, feats in variants:
        _fit_predict(con, seg, feats, fit, test, min_n)
        rows.append({"model": name} | _evaluate_pred(con))
    base = rows[0]["base_rate"]
    rows.append(
        {k: None for k in rows[0]}
        | {
            "model": "random (expected)",
            "rows": rows[0]["rows"],
            "base_rate": base,
            "p_at_100_rate": base,
            "p_at_1000_rate": base,
            "lift_at_100": 1.0,
            "lift_at_1000": 1.0,
            "top10_capture_share": 0.1,
            "log_loss_skill_share": 0.0,
        }
    )
    abl = []
    ablations = [(f"drop {f} ({FEATURE_LABELS[f]})", tuple(x for x in full if x != f)) for f in full]
    ablations.append(
        (
            "hail kept but without its 'no location' flag (merged into 0)",
            tuple("hail_only" if x == "hail" else x for x in full),
        )
    )
    for label, feats in ablations:
        _fit_predict(con, seg, feats, fit, test, min_n)
        e = _evaluate_pred(con)
        abl.append(
            {
                "variant": label,
                "p_at_100_rate": e["p_at_100_rate"],
                "p_at_1000_rate": e["p_at_1000_rate"],
                "lift_at_1000": e["lift_at_1000"],
                "top10_capture_share": e["top10_capture_share"],
                "log_loss_skill_share": e["log_loss_skill_share"],
                "lift_change_vs_full": e["lift_at_1000"] - rows[0]["lift_at_1000"],
                "skill_change_share": e["log_loss_skill_share"] - rows[0]["log_loss_skill_share"],
            }
        )
    _fit_predict(con, seg, full, fit, test, min_n)
    cal = _calibration(con)
    return {"rows": rows, "ablation": abl, "calibration": cal}


def h30_reroof_cycle_model(con) -> dict:
    """Parcel-quarter model of a roof permit in the next 365 days for commercial and multifamily parcels."""
    _build_h30_matrix(con)
    seg_info = q(
        con,
        f"""
        SELECT seg, count(*) AS rows, count(DISTINCT pin10) AS parcels,
          avg(y::INT) FILTER (WHERE d <= DATE '{TRAIN_END}') AS train_rate,
          avg(y::INT) FILTER (WHERE d >= DATE '{TEST_START}') AS test_rate,
          count(*) FILTER (WHERE d >= DATE '{TEST_START}') AS test_rows,
          avg((age <> 'unknown')::INT) AS age_known_share,
          avg((hail <> 'no location')::INT) AS hail_located_share,
          avg((roof <> 'none on record')::INT) FILTER (WHERE d >= DATE '{TEST_START}') AS roof_on_record_test_share,
          avg((viol = 'yes')::INT) AS roof_violation_share
        FROM m30 GROUP BY seg ORDER BY seg
    """,
    )
    roof_rates = q(
        con,
        f"""
        SELECT seg, roof AS roof_bucket,
          count(*) FILTER (WHERE d <= DATE '{TRAIN_END}') AS train_rows,
          avg(y::INT) FILTER (WHERE d <= DATE '{TRAIN_END}') AS train_rate,
          count(*) FILTER (WHERE d >= DATE '{TEST_START}') AS test_rows,
          avg(y::INT) FILTER (WHERE d >= DATE '{TEST_START}') AS test_rate
        FROM m30 GROUP BY seg, roof ORDER BY seg, roof
    """,
    )
    out = {}
    tuned = {}
    for seg in ("main", "flats"):
        scores = []
        for mn in MIN_N_GRID:
            _fit_predict(
                con,
                seg,
                MODEL_FEATURES,
                f"d <= DATE '{VAL_FIT_END}'",
                f"d >= DATE '{VAL_START}' AND d <= DATE '{VAL_END}'",
                mn,
            )
            scores.append((-_evaluate_pred(con)["log_loss_skill_share"], mn))
        best = min(scores)[1]
        tuned[seg] = {"min_cell_size": best, "validation_log_loss_skill": {str(mn): -s for s, mn in scores}}
        out[seg] = _h30_segment(con, seg, best)
    main = out["main"]["rows"][0]
    flats = out["flats"]["rows"][0]
    best_baseline = max(out["main"]["rows"][1:4], key=lambda r: r["lift_at_1000"])
    metrics = {
        "signals": main["rows"],
        "conversion": main["p_at_1000_rate"],
        "baseline": main["base_rate"],
        "lift": main["lift_at_1000"],
        "signals_per_week": 1000 / 13,
        "p_at_100_rate": main["p_at_100_rate"],
        "lift_at_100": main["lift_at_100"],
        "hits_at_1000": main["hits_at_1000"],
        "best_baseline": best_baseline["model"],
        "best_baseline_lift_at_1000": best_baseline["lift_at_1000"],
        "lift_vs_best_baseline": main["p_at_1000_rate"] / best_baseline["p_at_1000_rate"],
        "flats_p_at_1000_rate": flats["p_at_1000_rate"],
        "flats_base_rate": flats["base_rate"],
        "flats_lift_at_1000": flats["lift_at_1000"],
        "tuning": tuned,
        "segments": seg_info,
        "roof_age_rates": roof_rates,
        "precision": out["main"]["rows"],
        "ablation": out["main"]["ablation"],
        "calibration": out["main"]["calibration"],
        "flats_precision": out["flats"]["rows"],
        "flats_ablation": out["flats"]["ablation"],
        "flats_calibration": out["flats"]["calibration"],
    }
    return result(
        "H30",
        "Commercial and multifamily reroof cycle model (as-of quarters 2016-2023, time-split validation)",
        who="Commercial roofers, roof-coating and sheet-metal contractors, roof inspection and consulting firms",
        data="Permits (roofing flag), violations (roofing), Cook County sales (class), residential characteristics and "
        "energy benchmarking (year built), NEXRAD hail detections, geocoded addresses",
        signal="Parcel-quarter features known at the as-of date: years since the last roof permit, class code, "
        "building age, roofing violation in the prior 2 years, hail detection within ~1 km in the prior 3 years",
        target="A roof permit issued at the parcel in the 365 days after the as-of date. Train: as-of dates "
        "2016-2019; test: 2021-2023 (precision among the top 100 / 1,000 parcels per quarter, pooled over 12 quarters)",
        metrics=_round_deep(metrics),
        notes="Universe at each as-of date: parcels whose class (latest sale on or before the date) is 5xx commercial "
        "or 3xx multifamily 7+ ('main', parcels with no sale since 2010 are absent), and, separately, every 2-6 unit "
        "flat or mixed-use parcel of class 211/212 in the Assessor residential file ('flats'). A sale entering the "
        "universe is a known-at-date fact but sales are also a renovation trigger, so main-segment rates include "
        "newly sold buildings. Rates come from back-off cell tables (full cell, then dropping hail, violation, "
        "age, class in that order) with a minimum cell size chosen on a time-split validation (fit on as-of dates "
        f"through {VAL_FIT_END}, validate {VAL_START} to {VAL_END}) and shrunk toward the base rate with "
        f"{RATE_SHRINK} pseudo-observations. Ties in predicted rate are broken by a hash of parcel and date, so the "
        "top lists are deterministic. 'none on record' for the last roof permit is left-censored: permits start in "
        "2006, so it means no roof permit in the last 10 years at the 2016 as-of dates and 17 years at the 2023 ones. "
        "Building age comes from the residential file or energy benchmarking (buildings of 50k+ sq ft) and is "
        "'unknown' for most commercial parcels, so it carries little signal there; the 2025-2026 assessor snapshot "
        "describes today's building, and buildings built after the as-of year are treated as unknown. Hail "
        "detections start in March 2016, so the 3-year lookback is short for the 2016-2018 training dates. Parcel "
        "coordinates come from geocoded permits, violations, 311 requests and business licenses at the parcel's "
        "address, so parcels with no such record have 'no location'. The target is a permit, not a roof: commercial "
        "reroofs are often unpermitted or filed with other work, so every rate is a floor; roofing violation "
        "and roof-permit history only attach to a parcel through PIN or address.",
    )


# --- H31 / H32 / H33: business licenses --------------------------------------------------------------------
NON_PREMISES_DESC = (
    "Peddler|Special Event|Pharmaceutical|Pop-Up|Raffles|Valet|Mobile Food|Shared Kitchen User|Shared Housing|"
    "Affiliation|License Manager|Booting|Towing|Taxicab|Transportation Network|Scooter|Bicycle Messenger|"
    "Short Term Residential|Explosives|Navy Pier|Wrigley|Indoor Special|Outdoor Patio|Late Hour|Music and Dance|"
    "Sports License|Video Gaming|Weapons|Tobacco Sampler|Tobacco Dealer|Heliports|Emerging Business|"
    "Commercial Passenger|Seasonal Lakefront|Caterer|License Broker|Not-For-Profit Club|\\(PAV\\)"
)
NON_PREMISES_ACTIVITY = (
    "HOME BASED|MOVING ALONG THE PUBLIC WAY|STREET PERFORMER|PEDDLER|MOBILE FOOD|FOOD TRUCK|EXPEDITER|"
    "SPECIAL EVENT|POP UP"
)
LICENSE_GROUPS = (
    "food & drink",
    "personal services/beauty",
    "health/fitness/childcare",
    "retail",
    "auto",
    "other",
)
GROUP_PRIORITY = {
    "auto": 1,
    "food & drink": 2,
    "personal services/beauty": 3,
    "health/fitness/childcare": 4,
    "retail": 5,
    "other": 6,
}
LIC_HORIZON = "DATE '2026-12-31'"


def license_group_sql(desc: str, act: str) -> str:
    u = f"upper({desc} || ' | ' || coalesce({act}, ''))"
    return f"""CASE
      WHEN regexp_matches({u}, 'MOTOR VEHICLE|FILLING STATION|FUEL|GARAGE|CAR WASH|\\bTIRE|AUTO REPAIR|AUTOMOTIVE') THEN 'auto'
      WHEN {desc} IN ('Retail Food Establishment', 'Tavern', 'Wholesale Food Establishment',
                      'Consumption on Premises - Incidental Activity')
           OR regexp_matches({u}, 'DINING|PREPARATION AND SALE|LIQUOR ON PREMISES|CONSUMPTION OF LIQUOR|COFFEE|CATERING|BAKERY|RESTAURANT') THEN 'food & drink'
      WHEN regexp_matches({u}, '\\bHAIR\\b|\\bNAIL|SKIN CARE|MASSAGE|BARBER|TATTOO|SALON|COSMETOLOG|BEAUTY|ESTHETIC|BODY') THEN 'personal services/beauty'
      WHEN {desc} = 'Children''s Services Facility License'
           OR regexp_matches({u}, 'FITNESS|CHILD|DAY CARE|DAYCARE|HEALTH|MEDICAL|CLINIC|DENTAL|YOGA|GYM|WELLNESS|THERAP|PHARMACY') THEN 'health/fitness/childcare'
      WHEN {desc} IN ('Package Goods', 'Tobacco', 'Pawnbroker') OR {desc} LIKE 'Secondhand Dealer%'
           OR regexp_matches({u}, 'RETAIL SALES|SALE OF FURNITURE|SALE OF GENERAL MERCHANDISE|JEWEL|CELL PHONE|PAYMENT CENTER') THEN 'retail'
      ELSE 'other' END"""


def ensure_lic(con) -> None:
    """Temp tables: licp (premises licenses with group), nsite (one row per new business site), addr_acct."""
    ensure_r4(con)
    if con.execute("SELECT count(*) FROM duckdb_tables() WHERE table_name = 'lic_ready'").fetchone()[0]:
        return
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE licp AS
        SELECT row_id, license_id, account_number AS acct, site_number AS site, address_key, application_type AS app,
          issue_date, start_date, expiration_date, license_status AS status, status_change_date, application_date AS app_date,
          least(greatest(coalesce(expiration_date, issue_date + INTERVAL 1 YEAR), issue_date), issue_date + INTERVAL 5 YEAR)::DATE AS exp_eff,
          license_description AS descr, business_activity AS activity,
          {license_group_sql("license_description", "business_activity")} AS grp
        FROM biz_license_history
        WHERE address_key IS NOT NULL AND issue_date IS NOT NULL AND application_type IN ('ISSUE', 'RENEW', 'C_LOC', 'C_CAPA', 'C_EXPA', 'C_SBA')
          AND NOT regexp_matches(license_description, '{NON_PREMISES_DESC}')
          AND NOT regexp_matches(upper(coalesce(business_activity, '')), '{NON_PREMISES_ACTIVITY}')
    """)
    prio = " ".join(f"WHEN '{g}' THEN {n}" for g, n in GROUP_PRIORITY.items())
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE nsite AS
        WITH first_rec AS (
          SELECT acct, site, min(issue_date) AS first_any FROM licp GROUP BY acct, site
        ),
        iss AS (
          SELECT l.acct, l.site, f.first_any AS d, first(l.address_key ORDER BY l.row_id, l.license_id) AS address_key,
            first(l.grp ORDER BY CASE l.grp {prio} END, l.row_id, l.license_id) AS grp,
            min(l.app_date) AS app_date, min(l.expiration_date) AS min_exp, count(*) AS n_rows
          FROM licp l JOIN first_rec f ON f.acct = l.acct AND f.site = l.site AND l.issue_date = f.first_any
          WHERE l.app = 'ISSUE' GROUP BY l.acct, l.site, f.first_any
        )
        SELECT * FROM iss
    """)
    con.execute("""
        CREATE OR REPLACE TEMP TABLE addr_acct AS
        SELECT address_key, count(DISTINCT acct) AS n_acct FROM licp GROUP BY address_key
    """)
    con.execute("CREATE OR REPLACE TEMP TABLE lic_ready AS SELECT 1 AS x")


def _std_rate(rows: list[dict], sig_pred, ctl_pred, min_ctl: int = 5, relet_strata: bool = False) -> dict:
    """Rate of the control cells standardized to the signal cells' (group, year) mix. rows: grp, yr, cell, n, hits.

    With relet_strata the strata also split by whether the space is a re-let (cells C and D)."""
    sig: dict[tuple, list[int]] = {}
    ctl: dict[tuple, list[int]] = {}
    for r in rows:
        key = (r["grp"], r["yr"], r["cell"] in ("C", "D") if relet_strata else None)
        if sig_pred(r):
            t = sig.setdefault(key, [0, 0])
            t[0] += r["n"]
            t[1] += r["hits"]
        if ctl_pred(r):
            t = ctl.setdefault(key, [0, 0])
            t[0] += r["n"]
            t[1] += r["hits"]
    n = sum(v[0] for v in sig.values())
    hits = sum(v[1] for v in sig.values())
    usable = {k: v for k, v in sig.items() if k in ctl and ctl[k][0] >= min_ctl}
    wsum = sum(v[0] for v in usable.values())
    std = sum(v[0] / wsum * ctl[k][1] / ctl[k][0] for k, v in usable.items()) if wsum else None
    sig_rate_matched = sum(v[1] for v in usable.values()) / wsum if wsum else None
    ctl_n = sum(v[0] for v in ctl.values())
    ctl_hits = sum(v[1] for v in ctl.values())
    return {
        "signals": n,
        "rate": hits / n if n else None,
        "matched_signals": wsum,
        "matched_rate": sig_rate_matched,
        "control_signals": ctl_n,
        "control_raw_rate": ctl_hits / ctl_n if ctl_n else None,
        "control_std_rate": std,
        "lift": sig_rate_matched / std if std and sig_rate_matched is not None else None,
    }


def h31_new_business_legitimacy(con) -> dict:
    """New business license: does a build-out permit before it (or a prior tenant) tell lasting businesses apart?"""
    ensure_lic(con)
    max_issue = one(con, "SELECT max(issue_date) AS d FROM biz_license_history")["d"]
    cutoff = f"DATE '{max_issue}' - INTERVAL 30 MONTH"
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE s31 AS
        SELECT n.acct, n.site, n.d, n.address_key, n.grp, year(n.d) AS yr,
          EXISTS (SELECT 1 FROM p WHERE p.address_key = n.address_key AND {RENO_PREDICATE}
                  AND p.issue_date > n.d - INTERVAL 365 DAY AND p.issue_date <= n.d) AS reno,
          EXISTS (SELECT 1 FROM licp x WHERE x.address_key = n.address_key AND x.acct <> n.acct
                  AND x.issue_date < n.d) AS relet,
          EXISTS (SELECT 1 FROM licp x WHERE x.acct = n.acct AND x.site = n.site AND x.app = 'RENEW'
                  AND x.issue_date > n.d + INTERVAL 18 MONTH AND x.issue_date <= n.d + INTERVAL 30 MONTH) AS renew_win,
          EXISTS (SELECT 1 FROM licp x WHERE x.acct = n.acct AND x.site = n.site AND x.app = 'RENEW'
                  AND x.issue_date <= n.d + INTERVAL 30 MONTH AND x.start_date <= n.d + INTERVAL 24 MONTH
                  AND x.expiration_date >= n.d + INTERVAL 24 MONTH + INTERVAL 30 DAY) AS in_force,
          (n.min_exp IS NOT NULL AND n.min_exp <= n.d + INTERVAL 25 MONTH) AS due,
          coalesce(a.n_acct, 0) >= 6 AS multi
        FROM nsite n LEFT JOIN addr_acct a USING (address_key)
        WHERE n.d >= DATE '{R4_START}'
    """)
    rows = q(
        con,
        f"""
        SELECT grp, yr, (CASE WHEN reno AND relet THEN 'D' WHEN reno THEN 'B' WHEN relet THEN 'C' ELSE 'A' END) AS cell,
          multi, count(*) AS n, sum((renew_win OR in_force)::INT) AS hits, sum(renew_win::INT) AS renew_hits,
          sum(in_force::INT) AS force_hits
        FROM s31 WHERE d <= {cutoff} AND due GROUP BY ALL ORDER BY grp, yr, cell, multi
    """,
    )
    allr = list(rows)

    def reno_f(r):
        return r["cell"] in ("B", "D")

    def alone_f(r):
        return r["cell"] == "A"

    def relet_f(r):
        return r["cell"] == "C"

    def no_reno_f(r):
        return r["cell"] in ("A", "C")

    head = _std_rate(allr, reno_f, no_reno_f, relet_strata=True)
    vs_alone = _std_rate(allr, reno_f, alone_f)
    b_vs_a = _std_rate(allr, lambda r: r["cell"] == "B", alone_f)
    d_vs_c = _std_rate(allr, lambda r: r["cell"] == "D", relet_f)
    relet_vs_alone = _std_rate(allr, relet_f, alone_f)
    single = [r for r in allr if not r["multi"]]
    head_single = _std_rate(single, reno_f, no_reno_f, relet_strata=True)

    def cell_row(label: str, pred) -> dict:
        sel = [r for r in allr if pred(r)]
        n = sum(r["n"] for r in sel)
        return {
            "cell": label,
            "signals": n,
            "alive_rate": sum(r["hits"] for r in sel) / n if n else None,
            "renewed_in_window_rate": sum(r["renew_hits"] for r in sel) / n if n else None,
            "renewed_term_covering_24m_rate": sum(r["force_hits"] for r in sel) / n if n else None,
        }

    cells = [
        cell_row("all new licenses", lambda r: True),
        cell_row("A: new license alone (no build-out permit, no earlier licensee at the address)", alone_f),
        cell_row("B: build-out permit in prior 365 days, no earlier licensee", lambda r: r["cell"] == "B"),
        cell_row("C: re-let (earlier licensee of another account), no build-out permit", relet_f),
        cell_row("D: re-let with build-out permit", lambda r: r["cell"] == "D"),
        cell_row("any build-out permit (B + D)", reno_f),
        cell_row("any re-let (C + D)", lambda r: r["cell"] in ("C", "D")),
    ]
    by_group = []
    for g in LICENSE_GROUPS:
        gr = [r for r in allr if r["grp"] == g]
        h = _std_rate(gr, reno_f, no_reno_f, relet_strata=True)
        rl = _std_rate(gr, relet_f, alone_f)
        by_group.append(
            {
                "group": g,
                "new_licenses": sum(r["n"] for r in gr),
                "no_build_out_alive_rate": h["control_raw_rate"],
                "build_out_signals": h["signals"],
                "build_out_alive_rate": h["rate"],
                "build_out_lift": h["lift"],
                "relet_signals": rl["signals"],
                "relet_alive_rate": rl["rate"],
                "relet_lift": rl["lift"],
            }
        )
    by_year = []
    for y in sorted({r["yr"] for r in allr}):
        yr = [r for r in allr if r["yr"] == y]
        h = _std_rate(yr, reno_f, no_reno_f, relet_strata=True)
        n_all = sum(r["n"] for r in yr)
        by_year.append(
            {
                "year": y,
                "new_licenses": n_all,
                "alive_rate": sum(r["hits"] for r in yr) / n_all,
                "build_out_signals": h["signals"],
                "build_out_alive_rate": h["rate"],
                "no_build_out_alive_rate": h["control_raw_rate"],
                "build_out_lift": h["lift"],
            }
        )
    excluded = one(con, f"SELECT count(*) AS n FROM s31 WHERE d <= {cutoff} AND NOT due")["n"]
    vol = one(
        con,
        f"""
        SELECT count(*) / 52.0 AS v_all, count(*) FILTER (WHERE reno) / 52.0 AS v_reno
        FROM s31 WHERE d > DATE '{max_issue}' - INTERVAL 365 DAY
    """,
    )
    metrics = {
        "signals": head["signals"],
        "conversion": head["matched_rate"],
        "baseline": head["control_std_rate"],
        "lift": head["lift"],
        "signals_per_week": vol["v_reno"],
        "new_licenses_per_week": vol["v_all"],
        "all_signals": cells[0]["signals"],
        "excluded_not_yet_due": excluded,
        "all_alive_rate": cells[0]["alive_rate"],
        "no_build_out_raw_rate": head["control_raw_rate"],
        "alone_raw_rate": vs_alone["control_raw_rate"],
        "build_out_vs_alone_lift": vs_alone["lift"],
        "b_vs_a_lift": b_vs_a["lift"],
        "d_vs_c_lift": d_vs_c["lift"],
        "relet_vs_alone_lift": relet_vs_alone["lift"],
        "single_tenant_build_out_signals": head_single["signals"],
        "single_tenant_build_out_rate": head_single["matched_rate"],
        "single_tenant_baseline": head_single["control_std_rate"],
        "single_tenant_lift": head_single["lift"],
        "cells": cells,
        "by_group": by_group,
        "by_year": by_year,
    }
    return result(
        "H31",
        "New business license + build-out permit before it → business still operating 18-30 months later",
        who="B2B sellers to new businesses (insurance, payments/POS, signage, cleaning, security, accounting) who want "
        "to know which registrations are real and lasting",
        data="Chicago business licenses 2014+ (biz_license_history), permits",
        signal="First license issued (application type ISSUE) to an account at a site, for a premises-based license, "
        "with a renovation/build-out/new-construction permit at the address in the prior 365 days "
        "(vs the same without a permit, and vs a re-let space)",
        target="Same account and site still licensed 18-30 months later: a RENEW record issued in that window, or a "
        "license term in force on the day 24 months after the first license that was not cancelled or revoked "
        "before then",
        metrics=_round_deep(metrics),
        notes="Premises-based licenses only (peddlers, special events, pop-ups, valet, mobile food, home-based "
        "businesses, add-on permits such as outdoor patio and late hour are excluded). A site is an account number plus "
        "site number whose first record in the data is an ISSUE; sites that began before 2014 only show renewals, so "
        "signals start in 2016. Groups come from the license description and business activity text with this "
        "precedence: auto, food & drink, personal services/beauty, health/fitness/childcare, retail, other. "
        "'conversion' = survival of the build-out group; 'baseline' = survival of the alone group standardized to the "
        "build-out group's license group by year mix. A tenant that is renamed or changes account number counts as "
        "closed, and a license cancelled after renewal still counts as renewed, so survival is a proxy for "
        "'operating', not a measurement. The 'earlier licensee' test is by street address without unit, so large "
        "multi-tenant buildings look re-let; the multi-tenant rows show the effect. Signals stop 30 months before "
        "the newest license record. Do not add current Overture presence as a feature: it describes the business "
        "after the outcome (survivor bias).",
    )


# --- H32 --------------------------------------------------------------------------------------------------
def _row_end(alias: str, d: str) -> str:
    """End date of a license row as known on date d: cancellations count only once they have happened."""
    return (
        f"CASE WHEN {alias}.status IN ('AAC', 'REV') AND {alias}.status_change_date <= {d} "
        f"THEN least({alias}.status_change_date, {alias}.exp_eff) ELSE {alias}.exp_eff END"
    )


def _build_turnover_events(con, last_event: str) -> None:
    """Temp tables tev (storefront turnover events) and cev (same-account renewals at a sole-licensee address)."""
    ensure_lic(con)
    prio = " ".join(f"WHEN '{g}' THEN {n}" for g, n in GROUP_PRIORITY.items())
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE nad AS
        WITH first_rec AS (SELECT acct, address_key, min(issue_date) AS first_any FROM licp GROUP BY acct, address_key)
        SELECT l.acct, l.address_key AS k, f.first_any AS d, first(l.grp ORDER BY CASE l.grp {prio} END, l.row_id, l.license_id) AS grp,
          min(l.app_date) AS app_date
        FROM licp l JOIN first_rec f ON f.acct = l.acct AND f.address_key = l.address_key AND l.issue_date = f.first_any
        WHERE l.app = 'ISSUE' GROUP BY l.acct, l.address_key, f.first_any
    """)
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE prior_end AS
        SELECT n.acct, n.k, n.d, x.acct AS a_acct, max({_row_end("x", "n.d")}) AS a_end
        FROM nad n JOIN licp x ON x.address_key = n.k AND x.acct <> n.acct AND x.issue_date < n.d
        GROUP BY n.acct, n.k, n.d, x.acct
    """)
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE tev AS
        SELECT acct, k, d, grp, app_date, d - m_end AS gap_days FROM (
          SELECT n.acct, n.k, n.d, n.grp, n.app_date, pe.m_end,
            lag(n.d) OVER (PARTITION BY n.k ORDER BY n.d, n.acct) AS prev
          FROM nad n JOIN (SELECT acct, k, d, max(a_end) AS m_end, bool_or(a_end > d) AS in_force
                           FROM prior_end GROUP BY acct, k, d) pe USING (acct, k, d)
          WHERE NOT pe.in_force AND pe.m_end > n.d - INTERVAL 365 DAY AND pe.m_end <= n.d
            AND n.d >= DATE '{R4_START}'
        ) WHERE (prev IS NULL OR d - prev > 365) AND d <= {last_event}
    """)
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE cev AS
        SELECT acct, k, d, grp FROM (
          SELECT r.*, lag(r.d) OVER (PARTITION BY r.k ORDER BY r.d, r.acct) AS prev FROM (
            SELECT l.acct, l.address_key AS k, l.issue_date AS d,
              first(l.grp ORDER BY CASE l.grp {prio} END, l.row_id, l.license_id) AS grp
            FROM licp l WHERE l.app = 'RENEW' AND l.issue_date >= DATE '{R4_START}' AND l.issue_date <= {last_event}
            GROUP BY l.acct, l.address_key, l.issue_date
          ) r
          WHERE NOT EXISTS (
            SELECT 1 FROM licp x WHERE x.address_key = r.k AND x.acct <> r.acct AND x.issue_date <= r.d
              AND (x.issue_date > r.d - INTERVAL 365 DAY OR {_row_end("x", "r.d")} > r.d))
        ) WHERE prev IS NULL OR d - prev > 365
    """)
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE reno32 AS
        SELECT DISTINCT address_key AS k, issue_date AS d FROM p WHERE address_key IS NOT NULL AND {RENO_PREDICATE}
    """)


def _event_outcomes(con, ev_sql: str, name: str) -> None:
    """Temp table <name>: one row per event with renovation-permit outcomes around its date d."""
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE {name} AS
        SELECT e.k, e.d, e.grp, year(e.d) AS yr,
          min(t.d - e.d) FILTER (WHERE t.d > e.d AND t.d <= e.d + INTERVAL 365 DAY) AS days_after,
          coalesce(bool_or(t.d > e.d - INTERVAL 365 DAY AND t.d <= e.d), false) AS before_flag,
          coalesce(bool_or(t.d > e.d - INTERVAL 730 DAY AND t.d <= e.d - INTERVAL 365 DAY), false) AS own_earlier,
          first(t.d - e.d ORDER BY abs(t.d - e.d), t.d - e.d DESC)
            FILTER (WHERE t.d > e.d - INTERVAL 365 DAY AND t.d <= e.d + INTERVAL 365 DAY) AS nearest_signed
        FROM ({ev_sql}) e LEFT JOIN reno32 t ON t.k = e.k AND t.d > e.d - INTERVAL 730 DAY AND t.d <= e.d + INTERVAL 365 DAY
        GROUP BY e.k, e.d, e.grp
    """)


def _signed_summary(con, table: str, label: str) -> dict:
    r = one(
        con,
        f"""
        SELECT count(*) AS events, count(nearest_signed) AS with_permit,
          count(*) FILTER (WHERE nearest_signed < 0) AS permit_first, count(*) FILTER (WHERE nearest_signed >= 0) AS permit_after,
          median(nearest_signed) AS med, quantile_cont(nearest_signed, 0.25) AS p25, quantile_cont(nearest_signed, 0.75) AS p75
        FROM {table}
    """,
    )
    return {
        "reference_date": label,
        "events": r["events"],
        "with_permit_within_365_either_way": r["with_permit"],
        "permit_before_share": r["permit_first"] / r["with_permit"] if r["with_permit"] else None,
        "permit_on_or_after_share": r["permit_after"] / r["with_permit"] if r["with_permit"] else None,
        "median_signed_days": r["med"],
        "p25_signed_days": r["p25"],
        "p75_signed_days": r["p75"],
    }


def h32_storefront_turnover(con) -> dict:
    """New licensee at an address whose previous licensee's last license ended within 365 days -> build-out permit."""
    max_issue = one(con, "SELECT max(issue_date) AS d FROM biz_license_history")["d"]
    last_event = f"DATE '{max_issue}' - INTERVAL 365 DAY"
    _build_turnover_events(con, last_event)
    _event_outcomes(con, "SELECT k, d, grp FROM tev", "tx")
    _event_outcomes(con, "SELECT k, d, grp FROM cev", "cx")
    _event_outcomes(
        con,
        "SELECT k, app_date AS d, grp FROM tev WHERE app_date IS NOT NULL AND app_date >= DATE '2015-01-01'",
        "ax",
    )
    rows = []
    for name in ("tx", "cx"):
        rows += q(
            con,
            f"""
            SELECT '{name}' AS src, grp, yr, count(*) AS n, count(days_after) AS hits, count(*) FILTER (WHERE before_flag) AS before_hits,
              count(*) FILTER (WHERE own_earlier) AS own_hits
            FROM {name} GROUP BY ALL ORDER BY ALL
        """,
        )

    def pick(src, key_hits="hits"):
        return [
            {"grp": r["grp"], "yr": r["yr"], "cell": src, "n": r["n"], "hits": r[key_hits]}
            for r in rows
            if r["src"] == src
        ]

    after = _std_rate(pick("tx") + pick("cx"), lambda r: r["cell"] == "tx", lambda r: r["cell"] == "cx")
    before = _std_rate(
        pick("tx", "before_hits") + pick("cx", "before_hits"),
        lambda r: r["cell"] == "tx",
        lambda r: r["cell"] == "cx",
    )
    own = sum(r["own_hits"] for r in rows if r["src"] == "tx") / sum(r["n"] for r in rows if r["src"] == "tx")
    tm = one(
        con,
        "SELECT median(days_after) AS med, quantile_cont(days_after, 0.25) AS p25, quantile_cont(days_after, 0.75) AS p75, "
        "avg((days_after > 30)::INT) FILTER (WHERE days_after IS NOT NULL) AS after_30 FROM tx",
    )
    gap = one(
        con,
        "SELECT median(gap_days) AS med, quantile_cont(gap_days, 0.25) AS p25, quantile_cont(gap_days, 0.75) AS p75 FROM tev",
    )
    timing = [
        _signed_summary(con, "tx", "license issue date (turnover events)"),
        _signed_summary(con, "cx", "renewal issue date (control events)"),
        _signed_summary(con, "ax", "application created date (turnover events with an application date)"),
    ]
    app = one(
        con,
        """
        SELECT count(*) AS n, count(days_after) AS hits, avg(own_earlier::INT) AS own_rate
        FROM ax
    """,
    )
    lic_same = one(
        con,
        """
        SELECT count(*) AS n, count(t.days_after) AS hits FROM tx t
        WHERE EXISTS (SELECT 1 FROM tev e WHERE e.k = t.k AND e.d = t.d AND e.app_date IS NOT NULL
                      AND e.app_date >= DATE '2015-01-01')
    """,
    )
    lag = one(
        con,
        "SELECT median(d - app_date) AS med, quantile_cont(d - app_date, 0.9) AS p90 FROM tev WHERE app_date IS NOT NULL",
    )
    by_group = []
    for g in LICENSE_GROUPS:
        t = [r for r in rows if r["src"] == "tx" and r["grp"] == g]
        sub = [r for r in pick("tx") + pick("cx") if r["grp"] == g]
        h = _std_rate(sub, lambda r: r["cell"] == "tx", lambda r: r["cell"] == "cx")
        n = sum(r["n"] for r in t)
        if not n:
            continue
        by_group.append(
            {
                "group": g,
                "turnover_events": n,
                "permit_after_rate": h["rate"],
                "control_events": h["control_signals"],
                "control_rate": h["control_std_rate"],
                "lift": h["lift"],
                "permit_before_rate": sum(r["before_hits"] for r in t) / n,
            }
        )
    by_year = []
    for y in sorted({r["yr"] for r in rows if r["src"] == "tx"}):
        sub = [r for r in pick("tx") + pick("cx") if r["yr"] == y]
        h = _std_rate(sub, lambda r: r["cell"] == "tx", lambda r: r["cell"] == "cx")
        by_year.append(
            {
                "year": y,
                "turnover_events": h["signals"],
                "permit_after_rate": h["rate"],
                "control_rate": h["control_std_rate"],
                "lift": h["lift"],
            }
        )
    vol = one(
        con,
        f"""
        SELECT count(*) / 52.0 AS v FROM (
          SELECT n.d FROM nad n JOIN (SELECT acct, k, d, max(a_end) AS m_end, bool_or(a_end > d) AS in_force FROM prior_end GROUP BY acct, k, d) pe
            USING (acct, k, d)
          WHERE NOT pe.in_force AND pe.m_end > n.d - INTERVAL 365 DAY AND pe.m_end <= n.d
            AND n.d > DATE '{max_issue}' - INTERVAL 365 DAY)
    """,
    )["v"]
    groups = [
        {
            "definition": "Renovation/build-out/new-construction permit within 365 days AFTER the new license (headline)",
            "events": after["signals"],
            "turnover_rate": after["rate"],
            "control_rate": after["control_std_rate"],
            "lift": after["lift"],
        },
        {
            "definition": "Same permit within 365 days BEFORE the new license",
            "events": before["signals"],
            "turnover_rate": before["rate"],
            "control_rate": before["control_std_rate"],
            "lift": before["lift"],
        },
        {
            "definition": "Application-date view: permit within 365 days after the application was created",
            "events": app["n"],
            "turnover_rate": app["hits"] / app["n"] if app["n"] else None,
            "control_rate": None,
            "lift": None,
        },
        {
            "definition": "Same events measured from the license issue date (comparison for the row above)",
            "events": lic_same["n"],
            "turnover_rate": lic_same["hits"] / lic_same["n"] if lic_same["n"] else None,
            "control_rate": None,
            "lift": None,
        },
    ]
    metrics = {
        "signals": after["signals"],
        "conversion": after["rate"],
        "baseline": after["control_std_rate"],
        "lift": after["lift"],
        "signals_per_week": vol,
        "control_events": after["control_signals"],
        "control_raw_rate": after["control_raw_rate"],
        "own_earlier_window": own,
        "permit_before_rate": before["rate"],
        "permit_before_control_rate": before["control_std_rate"],
        "permit_before_lift": before["lift"],
        "median_days": tm["med"],
        "days_p25": tm["p25"],
        "days_p75": tm["p75"],
        "converted_after_30_days": tm["after_30"],
        "gap_days_median": gap["med"],
        "gap_days_p25": gap["p25"],
        "gap_days_p75": gap["p75"],
        "application_to_license_days_median": lag["med"],
        "application_to_license_days_p90": lag["p90"],
        "groups": groups,
        "timing": timing,
        "by_group": by_group,
        "by_year": by_year,
    }
    return result(
        "H32",
        "Storefront turnover (new licensee after the previous one lapsed) → build-out permit at the address",
        who="Build-out contractors, signage, equipment and fixtures suppliers, brokers, cleaning and security vendors",
        data="Chicago business licenses 2014+ (biz_license_history), permits (same renovation predicate as H26/food.py)",
        signal="First license (ISSUE) of an account at an address whose previous licensee's last license (expiration or "
        "cancellation known on that date) ended within the prior 365 days, with no other licensee in force "
        "(one per address per 365 days)",
        target="Renovation/build-out/new-construction permit at the address within 365 days after the license; "
        "control = same-account renewals at addresses with no other licensee in force and no new account in the "
        "prior 365 days, matched on license group and year; also the signed timing of the permit around the license "
        "and application dates",
        metrics=_round_deep(metrics),
        notes="Premises-based licenses only (same filter as H31). Addresses are street addresses without unit, so a "
        "permit for another tenant or the landlord counts for both groups; requiring no other licensee in force "
        "keeps the test to storefront-like addresses but cannot see unlicensed tenants. A turnover cannot be told from "
        "an owner who re-registers under a new account number, and a previous licensee that never renewed may "
        "simply have closed years earlier (hence the 365-day lapse limit). Cancellations use the status date only "
        "once it has happened. The feed lists a license only when it is issued (no row has an empty issue date), so "
        "'application created' is a back-dated field known only after issue: the application date gives the median "
        "extra days shown under timing, but it is not observable before the license. 'median_days' is days from "
        "license issue to the first permit among turnovers that converted; 'permit_before' counts a permit in the 365 "
        "days up to the license date (the build-out that precedes opening). The renewal control has fewer "
        "build-outs by construction (an operating tenant), so lift also partly measures 'new tenant vs continuing "
        "tenant'; compare the before and after rows.",
    )


# --- H33 --------------------------------------------------------------------------------------------------
H33_BUCKETS = ("commercial/industrial (5xx)", "mixed-use up to 6 units (212)", "multifamily 7+ (3xx)")


def h33_buildout_permit_to_new_license(con) -> dict:
    """Reverse of H32: a build-out permit at a space with no licensee -> a new business registers there.

    Reasoning: H32 shows the build-out usually precedes the license (median 77 days before it), and the permit feed is
    public the day it is issued, while the license record appears only at issue. A seller of signage, POS, insurance,
    cleaning or furniture can therefore reach the new tenant earlier through the permit than through the license.
    H21/H26 showed this for restaurants; this tests it for every premises-based license group.
    """
    max_issue = one(con, "SELECT max(issue_date) AS d FROM biz_license_history")["d"]
    last_event = f"DATE '{max_issue}' - INTERVAL 365 DAY"
    _build_turnover_events(con, last_event)
    bucket_list = ", ".join(f"'{b}'" for b in H33_BUCKETS)
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE s33 AS
        SELECT k, d, bucket, CASE WHEN cost >= 100000 THEN '$100k+' WHEN cost >= 25000 THEN '$25k-$100k'
                                  WHEN cost > 0 THEN 'under $25k' ELSE 'no cost reported' END AS cost_band FROM (
          SELECT r.k, r.d, r.cost, ac.bucket, lag(r.d) OVER (PARTITION BY r.k ORDER BY r.d) AS prev
          FROM (SELECT address_key AS k, issue_date AS d, max(coalesce(reported_cost, 0)) AS cost FROM p
                WHERE address_key IS NOT NULL AND {RENO_PREDICATE} GROUP BY 1, 2) r
          JOIN (SELECT DISTINCT address_key, bucket FROM addr_cls WHERE bucket IN ({bucket_list})) ac
            ON ac.address_key = r.k
          WHERE NOT EXISTS (SELECT 1 FROM licp x WHERE x.address_key = r.k AND x.issue_date <= r.d
                            AND {_row_end("x", "r.d")} > r.d)
        ) WHERE (prev IS NULL OR d - prev > 365) AND d >= DATE '{R4_START}' AND d <= {last_event}
    """)
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE qd33 AS
        SELECT unnest(generate_series(DATE '{R4_START}', {last_event}, INTERVAL 3 MONTH))::DATE AS q
    """)
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE pool33 AS
        SELECT a.address_key AS k, qd33.q AS d, a.bucket FROM
          (SELECT DISTINCT address_key, bucket FROM addr_cls WHERE bucket IN ({bucket_list})) a CROSS JOIN qd33
        WHERE NOT EXISTS (SELECT 1 FROM reno32 t WHERE t.k = a.address_key
                          AND t.d > qd33.q - INTERVAL 365 DAY AND t.d <= qd33.q + INTERVAL 365 DAY)
          AND NOT EXISTS (SELECT 1 FROM licp x WHERE x.address_key = a.address_key AND x.issue_date <= qd33.q
                          AND {_row_end("x", "qd33.q")} > qd33.q)
    """)
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE pool33b AS
        SELECT DISTINCT a.address_key AS k, qd33.q AS d, a.bucket FROM
          (SELECT DISTINCT address_key, bucket FROM addr_cls WHERE bucket IN ({bucket_list})) a CROSS JOIN qd33
        WHERE EXISTS (SELECT 1 FROM p x WHERE x.address_key = a.address_key AND NOT {RENO_PREDICATE}
                      AND x.issue_date > qd33.q - INTERVAL 90 DAY AND x.issue_date <= qd33.q)
          AND NOT EXISTS (SELECT 1 FROM reno32 t WHERE t.k = a.address_key
                          AND t.d > qd33.q - INTERVAL 365 DAY AND t.d <= qd33.q + INTERVAL 365 DAY)
          AND NOT EXISTS (SELECT 1 FROM licp x WHERE x.address_key = a.address_key AND x.issue_date <= qd33.q
                          AND {_row_end("x", "qd33.q")} > qd33.q)
    """)
    for name in ("s33", "pool33", "pool33b"):
        con.execute(f"""
            CREATE OR REPLACE TEMP TABLE {name}_x AS
            SELECT e.k, e.d, e.bucket, year(e.d) AS yr,
              min(n.d - e.d) FILTER (WHERE n.d > e.d AND n.d <= e.d + INTERVAL 365 DAY) AS days_after,
              first(n.grp ORDER BY n.d, n.acct) FILTER (WHERE n.d > e.d AND n.d <= e.d + INTERVAL 365 DAY) AS first_grp,
              coalesce(bool_or(n.d > e.d - INTERVAL 730 DAY AND n.d <= e.d - INTERVAL 365 DAY), false) AS own_earlier
              {", e.cost_band" if name == "s33" else ""}
            FROM {name} e LEFT JOIN nad n ON n.k = e.k AND n.d > e.d - INTERVAL 730 DAY AND n.d <= e.d + INTERVAL 365 DAY
            GROUP BY e.k, e.d, e.bucket{", e.cost_band" if name == "s33" else ""}
        """)
    rows = []
    for name, src in (("s33_x", "sig"), ("pool33_x", "ctl"), ("pool33b_x", "busy")):
        cost = "cost_band" if name == "s33_x" else "'-'"
        rows += [
            {
                "grp": r["bucket"],
                "yr": r["yr"],
                "cell": src,
                "n": r["n"],
                "hits": r["hits"],
                "own": r["own"],
                "cost": r["cost"],
            }
            for r in q(
                con,
                f"""
            SELECT bucket, yr, {cost} AS cost, count(*) AS n, count(days_after) AS hits,
              count(*) FILTER (WHERE own_earlier) AS own
            FROM {name} GROUP BY ALL ORDER BY ALL
        """,
            )
        ]
    head = _std_rate(rows, lambda r: r["cell"] == "sig", lambda r: r["cell"] == "ctl")
    busy = _std_rate(rows, lambda r: r["cell"] == "sig", lambda r: r["cell"] == "busy")
    by_cost = []
    for band in ("no cost reported", "under $25k", "$25k-$100k", "$100k+"):
        h = _std_rate(
            rows, lambda r, band=band: r["cell"] == "sig" and r["cost"] == band, lambda r: r["cell"] == "ctl"
        )
        hb = _std_rate(
            rows, lambda r, band=band: r["cell"] == "sig" and r["cost"] == band, lambda r: r["cell"] == "busy"
        )
        by_cost.append(
            {
                "permit_cost": band,
                "signals": h["signals"],
                "new_license_rate": h["rate"],
                "control_rate": h["control_std_rate"],
                "lift": h["lift"],
                "busy_control_rate": hb["control_std_rate"],
                "lift_vs_busy": hb["lift"],
            }
        )
    own = sum(r["own"] for r in rows if r["cell"] == "sig") / sum(r["n"] for r in rows if r["cell"] == "sig")
    tm = one(
        con,
        """
        SELECT median(days_after) AS med, quantile_cont(days_after, 0.25) AS p25, quantile_cont(days_after, 0.75) AS p75,
          avg((days_after <= 90)::INT) FILTER (WHERE days_after IS NOT NULL) AS within_90,
          avg((days_after <= 180)::INT) FILTER (WHERE days_after IS NOT NULL) AS within_180,
          avg((days_after > 30)::INT) FILTER (WHERE days_after IS NOT NULL) AS after_30
        FROM s33_x
    """,
    )
    late = one(
        con,
        "SELECT count(*) AS n, count(*) FILTER (WHERE days_after > 30) AS hits FROM s33_x",
    )
    by_group = q(
        con,
        """
        SELECT first_grp AS license_group, count(*) AS new_licenses, median(days_after) AS median_days,
          quantile_cont(days_after, 0.25) AS p25_days, quantile_cont(days_after, 0.75) AS p75_days
        FROM s33_x WHERE days_after IS NOT NULL GROUP BY 1 ORDER BY count(*) DESC, 1
    """,
    )
    tot = sum(r["new_licenses"] for r in by_group)
    for r in by_group:
        r["share_of_conversions"] = r["new_licenses"] / tot
    by_bucket = []
    for b in H33_BUCKETS:
        sub = [r for r in rows if r["grp"] == b]
        h = _std_rate(sub, lambda r: r["cell"] == "sig", lambda r: r["cell"] == "ctl")
        if h["signals"]:
            by_bucket.append(
                {
                    "class": b,
                    "signals": h["signals"],
                    "new_license_rate": h["rate"],
                    "control_rate": h["control_std_rate"],
                    "lift": h["lift"],
                }
            )
    by_year = []
    for y in sorted({r["yr"] for r in rows if r["cell"] == "sig"}):
        sub = [r for r in rows if r["yr"] == y]
        h = _std_rate(sub, lambda r: r["cell"] == "sig", lambda r: r["cell"] == "ctl")
        by_year.append(
            {
                "year": y,
                "signals": h["signals"],
                "new_license_rate": h["rate"],
                "control_rate": h["control_std_rate"],
                "lift": h["lift"],
            }
        )
    vol = one(
        con,
        f"""
        SELECT count(*) / 52.0 AS v FROM (
          SELECT DISTINCT r.k, r.d FROM (SELECT DISTINCT address_key AS k, issue_date AS d FROM p
                WHERE address_key IS NOT NULL AND {RENO_PREDICATE}) r
          JOIN (SELECT DISTINCT address_key FROM addr_cls WHERE bucket IN ({bucket_list})) ac ON ac.address_key = r.k
          WHERE r.d > DATE '{max_issue}' - INTERVAL 365 DAY
            AND NOT EXISTS (SELECT 1 FROM licp x WHERE x.address_key = r.k AND x.issue_date <= r.d
                            AND {_row_end("x", "r.d")} > r.d))
    """,
    )["v"]
    metrics = {
        "signals": head["signals"],
        "conversion": head["rate"],
        "baseline": head["control_std_rate"],
        "lift": head["lift"],
        "signals_per_week": vol,
        "control_events": head["control_signals"],
        "control_raw_rate": head["control_raw_rate"],
        "busy_control_events": busy["control_signals"],
        "busy_control_rate": busy["control_std_rate"],
        "lift_vs_busy_control": busy["lift"],
        "own_earlier_window": own,
        "lift_vs_own_earlier": head["rate"] / own if own else None,
        "median_days": tm["med"],
        "days_p25": tm["p25"],
        "days_p75": tm["p75"],
        "within_90_days_share": tm["within_90"],
        "within_180_days_share": tm["within_180"],
        "converted_after_30_days": tm["after_30"],
        "rate_if_license_31_plus_days_later": late["hits"] / late["n"] if late["n"] else None,
        "by_group": by_group,
        "by_class": by_bucket,
        "by_cost": by_cost,
        "by_year": by_year,
    }
    return result(
        "H33",
        "Build-out permit at a space with no licensee → a new business registers there within 365 days",
        who="Sellers to brand-new businesses: signage, POS/payments, insurance, cleaning, security, furniture, "
        "telecom, accountants, and the brokers and GCs that serve them",
        data="Permits (renovation, build-out text, new construction), Chicago business licenses 2014+, parcel classes "
        "from sales",
        signal="Renovation/alteration, interior build-out or new-construction permit at an address of class commercial/"
        "industrial (5xx), mixed-use (212) or multifamily 7+ (3xx) with no business license in force at that date "
        "(one per address per 365 days)",
        target="A new account's first (ISSUE) premises license at the address within 365 days after the permit; control "
        "= same-class address-quarters with no licensee in force and no renovation permit within a year either side, "
        "matched on class and year",
        metrics=_round_deep(metrics),
        notes="Reasoning: H32 shows build-outs mostly precede the new license, and the permit is public the day it is "
        "issued while the license only appears when issued, so the permit is the earlier, observable signal for "
        "anyone selling to a new business. Class comes from the latest sale or residential file, so addresses with no "
        "sale since 2010 are not in the universe. 'In force' uses license terms and cancellations known on the "
        "permit date. The license group of the first new licensee is a result, not something the permit "
        "tells you in advance. Premises-based licenses only (same filter as H31); unlicensed businesses, "
        "professional offices without a license and licenses under 2014 history are invisible, so conversion is a "
        "floor. Addresses are by street address without unit, so a permit for one tenant counts for the whole "
        "building. Signals stop 365 days before the newest license record.",
    )


HYPOTHESES: dict[str, Callable] = {
    "H01": h01_solar_neighbors,
    "H02": h02_reroof_then_solar,
    "H03": h03_reroof_neighbors,
    "H04": h05_hail,
    "H05": h05b_wind,
    "H06": h06_basement_water,
    "H07": h07_complaint_to_violation,
    "H08": h08_porch_request,
    "H09": h09_vacant_to_sale,
    "H10": h10_unpermitted_work,
    "H11": h11_lead_test,
    "H12": h12_roof_age,
    "H13": h13_masonry_walls,
    "H14": h14_no_ac,
    "H15": h15_condition,
    "H16": h16_energy,
    "H17": h17_complaint_chain,
    "H18": h18_repeat_investors,
    "H19": h19_tree_emergency,
    "H20": h20_rodent_to_violation,
    "H21": h21_food_takeover,
    "H22": h22_seasonality,
    "H23": h23_pest_persistence,
    "H24": h24_plumbing_permit,
    "H25": h25_hood_hvac_permit,
    "H26": h26_out_of_business,
    "H27": h27_hmda_tracts,
    "H28": h28_radar_hail,
    "H29": h29_trades_after_big_permit,
    "H30": h30_reroof_cycle_model,
    "H31": h31_new_business_legitimacy,
    "H32": h32_storefront_turnover,
    "H33": h33_buildout_permit_to_new_license,
}


# ----------------------------------------------------------------------------------------------------------
ROUND4 = ("H29", "H30", "H31", "H32", "H33")


def fmt(x, pct=False) -> str:
    if x is None:
        return "—"
    return f"{100 * x:.1f}%" if pct else (f"{x:.2f}" if isinstance(x, float) else str(x))


def render(results: list[dict], generated: str) -> str:
    L = [
        f"# Signal lab — {generated}",
        "",
        "Creative lead hypotheses tested against Chicago history. Reproduce with "
        "`uv run python research/signal_lab/lab.py`. Verdicts: **Strong** = lift ≥ 3 with ≥ 5 signals/week; "
        "**Useful** = lift ≥ 1.8; **Weak** = lift ≥ 1.25; otherwise **No signal**. Permits capture permitted work "
        "only, so conversion rates are floors.",
        "",
        "## Leaderboard",
        "",
        "| # | Hypothesis | Verdict | Lift | Conversion | Baseline | Signals/week | Who it's for |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    order = {"Strong": 0, "Useful": 1, "Weak": 2, "Descriptive": 3, "No signal": 4}
    ranked = sorted(results, key=lambda r: (order[r["verdict"]], -(r["metrics"].get("lift") or 0)))
    for r in ranked:
        m = r["metrics"]
        ratio = r["id"] in ("H04", "H05")
        L.append(
            f"| {r['id']} | {r['title']} | **{r['verdict']}** | {fmt(m.get('lift'))}× | "
            f"{fmt(m.get('conversion')) if ratio else fmt(m.get('conversion'), True)} | "
            f"{fmt(m.get('baseline')) if ratio else fmt(m.get('baseline'), True)} | "
            f"{fmt(round(m['signals_per_week'], 1) if m.get('signals_per_week') else None)} | {r['who']} |"
        )
    for r in ranked:
        m = r["metrics"]
        L += [
            "",
            f"## {r['id']} — {r['title']}",
            "",
            f"- **Signal:** {r['signal']}",
            f"- **Target:** {r['target']}",
            f"- **Data:** {r['data']}",
            f"- **Verdict:** {r['verdict']}",
        ]
        if r["notes"]:
            L.append(f"- **Notes:** {r['notes']}")
        if "median_days" in m:
            L.append(
                f"- Signals tested: {m['signals']:,}; conversion {fmt(m['conversion'], True)} vs baseline "
                f"{fmt(m['baseline'], True)}; median {m['median_days']} days to target"
            )
        for key in (
            "by_neighbors",
            "groups",
            "complaint_basis",
            "loyalty",
            "by_year",
            "strata",
            "by_trade",
            "by_class",
            "by_cost",
            "by_group",
            "by_bucket",
            "cells",
            "timing",
            "segments",
            "roof_age_rates",
            "precision",
            "ablation",
            "calibration",
            "flats_precision",
            "flats_ablation",
            "flats_calibration",
        ):
            if key in m and m[key]:
                rows = m[key]
                cols = list(rows[0].keys())
                L += ["", "| " + " | ".join(cols) + " |", "| " + " | ".join("---" for _ in cols) + " |"]
                for row in rows[:16]:
                    L.append(
                        "| "
                        + " | ".join(
                            fmt(
                                v,
                                pct=(
                                    "rate" in c
                                    or "share" in c
                                    or c
                                    in (
                                        "conversion",
                                        "prior_window",
                                        "signal",
                                        "matched_control",
                                        "control_conversion",
                                    )
                                ),
                            )
                            if isinstance(v, float)
                            else ("—" if v is None else str(v))
                            for c, v in row.items()
                        )
                        + " |"
                    )
        if r["id"] in ROUND4:
            scalars = [
                f"{k} = {fmt(v)}"
                for k, v in m.items()
                if isinstance(v, (int, float)) and not isinstance(v, bool)
            ]
            L += ["", "- Key numbers (rates are fractions): " + "; ".join(scalars)]
            if m.get("tuning"):
                L.append(f"- Tuning (time-split validation): {json.dumps(m['tuning'], sort_keys=True)}")
        if r["id"] in ("H04", "H05") and "near_after" in m:
            L.append(
                f"- Near storms: {m['near_after']} reroof permits in the 120 days after vs {m['near_year_before']} "
                f"in the same window a year earlier; elsewhere: {m['far_after']} vs {m['far_year_before']}; "
                f"{m['storm_reports']} storm reports."
            )
    L.append("")
    return "\n".join(L)


def main() -> int:
    wanted = sys.argv[1:] or list(HYPOTHESES)
    partial = set(wanted) != set(HYPOTHESES)
    con = duckdb.connect(str(DB), read_only=True)
    con.execute("SET memory_limit = '10GB'")
    prepare(con)
    results = []
    for hid in wanted:
        print(f"running {hid} ...", flush=True)
        results.append(HYPOTHESES[hid](con))
    generated = date.today().isoformat()
    OUT.mkdir(parents=True, exist_ok=True)
    stem = f"{OUT / f'signal-lab-{generated}'}{'.partial' if partial else ''}"
    Path(stem + ".json").write_text(json.dumps(_round_deep(results), indent=2, default=str))
    Path(stem + ".md").write_text(render(results, generated))
    print(f"wrote {stem}.md")
    for r in sorted(results, key=lambda r: -(r["metrics"].get("lift") or 0)):
        print(f"  {r['id']} {r['verdict']:<10} lift={fmt(r['metrics'].get('lift'))} {r['title']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
