"""Signal lab: test creative lead hypotheses against Chicago history and rank them.

    uv run python research/signal_lab/lab.py              # all hypotheses
    uv run python research/signal_lab/lab.py H01 H06      # selected ones

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
import sys
from collections.abc import Callable
from datetime import date
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

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
}


# ----------------------------------------------------------------------------------------------------------
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
        for key in ("by_neighbors", "groups", "complaint_basis", "loyalty", "by_year", "strata"):
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
    con = duckdb.connect(str(DB), read_only=True)
    con.execute("SET memory_limit = '10GB'")
    prepare(con)
    results = []
    for hid in wanted:
        print(f"running {hid} ...", flush=True)
        results.append(HYPOTHESES[hid](con))
    generated = date.today().isoformat()
    OUT.mkdir(parents=True, exist_ok=True)
    stem = OUT / f"signal-lab-{generated}"
    stem.with_suffix(".json").write_text(json.dumps(_round_deep(results), indent=2, default=str))
    stem.with_suffix(".md").write_text(render(results, generated))
    print(f"wrote {stem}.md")
    for r in sorted(results, key=lambda r: -(r["metrics"].get("lift") or 0)):
        print(f"  {r['id']} {r['verdict']:<10} lift={fmt(r['metrics'].get('lift'))} {r['title']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
