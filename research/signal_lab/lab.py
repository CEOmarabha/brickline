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

from engine.score.signals import one, prepare_base, q  # noqa: E402

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
        SELECT reroofed, count(*) AS parcels, avg(y::INT) AS rate FROM u WHERE NOT already GROUP BY 1
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
        for key in ("by_neighbors", "groups", "by_year"):
            if key in m and m[key]:
                rows = m[key]
                cols = list(rows[0].keys())
                L += ["", "| " + " | ".join(cols) + " |", "| " + " | ".join("---" for _ in cols) + " |"]
                for row in rows[:16]:
                    L.append(
                        "| "
                        + " | ".join(
                            fmt(v, pct=("rate" in c or c == "conversion")) if isinstance(v, float) else str(v)
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
    stem.with_suffix(".json").write_text(json.dumps(results, indent=2, default=str))
    stem.with_suffix(".md").write_text(render(results, generated))
    print(f"wrote {stem}.md")
    for r in sorted(results, key=lambda r: -(r["metrics"].get("lift") or 0)):
        print(f"  {r['id']} {r['verdict']:<10} lift={fmt(r['metrics'].get('lift'))} {r['title']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
