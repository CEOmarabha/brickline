"""Historical backtests of candidate lead signals on Chicago public records.

Each backtest asks: when signal X appears at a property (or company), how often does a real job Y follow,
how soon, and how does that compare with a baseline? Results feed the lead-scoring formulas.

    uv run python -m engine.warehouse sync && uv run python -m engine.warehouse build
    uv run python research/backtests/run_backtests.py

Writes research/findings/backtests-<date>.md and .json.
"""

from __future__ import annotations

import json
import math
import sys
from datetime import date
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from engine.score.signals import (  # noqa: E402
    INVESTOR_RE,
    MAJOR,
    PARCEL_FEATURES,
    build_parcel_features,
    fit_combo_rates,
    one,
    prepare_base,
    q,
)

DB = Path("data/warehouse.duckdb")
OUT = Path("research/findings")

TRADES_SHARED = ["roofing", "masonry", "porch", "windows_doors", "electrical", "plumbing", "hvac"]
FEATURES = PARCEL_FEATURES


# --------------------------------------------------------------------------------------------------
# BT1: demolition permit -> new-construction permit at the same property
# --------------------------------------------------------------------------------------------------
def bt_demolition(con) -> dict:
    con.execute("""
        CREATE OR REPLACE TEMP TABLE demo AS
        SELECT prop, min(issue_date) AS demo_date, max(reported_cost) AS demo_cost
        FROM p WHERE permit_type = 'PERMIT - WRECKING/DEMOLITION'
          AND issue_date BETWEEN DATE '2010-01-01' AND DATE '2024-10-31'
        GROUP BY prop
    """)
    con.execute("""
        CREATE OR REPLACE TEMP TABLE nc AS
        SELECT id, prop, application_date, issue_date, reported_cost
        FROM p WHERE permit_type = 'PERMIT - NEW CONSTRUCTION' AND application_date IS NOT NULL
    """)
    con.execute("""
        CREATE OR REPLACE TEMP TABLE demo_nc AS
        SELECT d.prop, d.demo_date,
               min(n.application_date) AS nc_app, min(n.issue_date) AS nc_issue,
               max(n.reported_cost) AS nc_cost
        FROM demo d LEFT JOIN nc n
          ON n.prop = d.prop
         AND n.issue_date >= d.demo_date - INTERVAL 180 DAY
         AND n.issue_date <= d.demo_date + INTERVAL 730 DAY
        GROUP BY ALL
    """)
    summary = one(
        con,
        """
        SELECT count(*) AS demolitions,
          avg((nc_issue IS NOT NULL)::INT) AS nc_within_2y,
          avg((nc_issue IS NOT NULL AND nc_app > demo_date)::INT) AS nc_applied_after_demo,
          median(nc_app - demo_date) FILTER (WHERE nc_issue IS NOT NULL) AS median_days_demo_to_nc_application,
          median(nc_issue - demo_date) FILTER (WHERE nc_issue IS NOT NULL) AS median_days_demo_to_nc_issue,
          quantile_cont(nc_issue - demo_date, 0.25) FILTER (WHERE nc_issue IS NOT NULL) AS p25_days_to_nc_issue,
          quantile_cont(nc_issue - demo_date, 0.75) FILTER (WHERE nc_issue IS NOT NULL) AS p75_days_to_nc_issue,
          median(nc_cost) FILTER (WHERE nc_issue IS NOT NULL) AS median_nc_reported_cost
        FROM demo_nc
    """,
    )
    lonely = one(
        con,
        """
        SELECT count(*) AS demolitions_without_nc_within_60d,
          avg((nc_issue IS NOT NULL)::INT) AS later_nc_61_730d
        FROM (
          SELECT d.prop, d.demo_date, min(n.issue_date) AS nc_issue
          FROM demo d LEFT JOIN nc n ON n.prop = d.prop
           AND n.issue_date > d.demo_date + INTERVAL 60 DAY AND n.issue_date <= d.demo_date + INTERVAL 730 DAY
          WHERE NOT EXISTS (SELECT 1 FROM nc n2 WHERE n2.prop = d.prop
                            AND n2.issue_date BETWEEN d.demo_date - INTERVAL 180 DAY
                                                  AND d.demo_date + INTERVAL 60 DAY)
          GROUP BY ALL
        )
    """,
    )
    summary.update(lonely)
    recall = one(
        con,
        """
        SELECT count(*) AS nc_permits_2012_2026,
          avg((EXISTS (SELECT 1 FROM demo d WHERE d.prop = n.prop
                AND d.demo_date BETWEEN n.application_date - INTERVAL 730 DAY AND n.application_date))::INT)
            AS share_preceded_by_demo
        FROM nc n WHERE n.issue_date >= DATE '2012-01-01'
    """,
    )
    by_year = q(
        con,
        """
        SELECT year(demo_date) AS year, count(*) AS demolitions,
               round(avg((nc_issue IS NOT NULL)::INT), 3) AS nc_within_2y
        FROM demo_nc GROUP BY 1 ORDER BY 1
    """,
    )
    # Who is named on the follow-on new-construction permits (opportunity for subs who track demolitions)
    roles = q(
        con,
        """
        WITH f AS (
          SELECT n.id FROM demo d JOIN nc n ON n.prop = d.prop
           AND n.issue_date BETWEEN d.demo_date - INTERVAL 180 DAY AND d.demo_date + INTERVAL 730 DAY
        )
        SELECT role, round(count(DISTINCT permit_id) / (SELECT count(DISTINCT id) FROM f), 3) AS share_named
        FROM permit_parties WHERE permit_id IN (SELECT id FROM f)
          AND role IN ('gc', 'electrical', 'plumbing', 'hvac', 'masonry', 'architect')
        GROUP BY role ORDER BY share_named DESC
    """,
    )
    weekly = one(
        con,
        """
        SELECT round(count(*) / 52.0, 1) AS demolitions_per_week_last_year
        FROM p WHERE permit_type = 'PERMIT - WRECKING/DEMOLITION'
          AND issue_date >= (SELECT max(issue_date) FROM p) - INTERVAL 365 DAY
    """,
    )
    return {
        "summary": summary,
        "recall": recall,
        "by_year": by_year,
        "roles_on_followon_nc": roles,
        "volume": weekly,
    }


# --------------------------------------------------------------------------------------------------
# BT2: property sale -> trade permits in the following year (within-property pre/post comparison)
# --------------------------------------------------------------------------------------------------
def bt_sale(con) -> dict:
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE s AS
        SELECT pin10, sale_date, sale_price, class,
          CASE
            WHEN class IN ('202','203','204','205','206','207','208','209','210','234','278','295')
              THEN 'single-family'
            WHEN class IN ('211','212') THEN '2-6 unit flat'
            WHEN class = '299' THEN 'condo unit'
            WHEN class LIKE '3%' OR class LIKE '9%' THEN 'apartment 7+'
            WHEN class LIKE '5%' OR class LIKE '6%' OR class LIKE '7%' OR class LIKE '8%'
              THEN 'commercial/industrial'
            WHEN class LIKE '1%' THEN 'vacant land'
            ELSE 'other'
          END AS segment,
          regexp_matches(upper(coalesce(buyer_name, '')), '{INVESTOR_RE}') AS investor_buyer
        FROM sales
        WHERE NOT filtered_out AND NOT is_multisale
          AND sale_date BETWEEN DATE '2012-01-01' AND DATE '2025-06-30'
    """)
    flags = ", ".join(f"bool_or(t_{t}) AS {t}" for t in TRADES_SHARED + ["solar", "interior_buildout"])
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE s_win AS
        SELECT s.pin10, s.sale_date, s.segment, s.investor_buyer, w.win, {flags},
               bool_or({MAJOR}) AS major, count(p.id) > 0 AS any_permit,
               min(p.issue_date - s.sale_date) FILTER (WHERE w.win = 'post') AS first_days
        FROM s
        CROSS JOIN (VALUES ('pre'), ('post')) w(win)
        LEFT JOIN p ON p.pin10 = s.pin10
          AND ((w.win = 'post' AND p.issue_date > s.sale_date AND p.issue_date <= s.sale_date + INTERVAL 365 DAY)
            OR (w.win = 'pre' AND p.issue_date > s.sale_date - INTERVAL 730 DAY
                AND p.issue_date <= s.sale_date - INTERVAL 365 DAY))
        GROUP BY ALL
    """)
    trades = TRADES_SHARED + ["solar", "interior_buildout", "major", "any_permit"]
    rows = []
    for seg_expr, label in [
        ("segment", None),
        (
            "segment || CASE WHEN investor_buyer THEN ' / investor buyer' ELSE ' / individual buyer' END",
            "buyer",
        ),
    ]:
        sel = ", ".join(
            f"avg(coalesce({t}, false)::INT) FILTER (WHERE win='post') AS post_{t}, "
            f"avg(coalesce({t}, false)::INT) FILTER (WHERE win='pre') AS pre_{t}"
            for t in trades
        )
        for r in q(
            con,
            f"""
            SELECT {seg_expr} AS segment, count(*) FILTER (WHERE win='post') AS sales, {sel}
            FROM s_win WHERE segment IN ('single-family','2-6 unit flat','apartment 7+','commercial/industrial')
            GROUP BY 1 ORDER BY sales DESC
        """,
        ):
            r["cut"] = label or "segment"
            rows.append(r)
    timing = q(
        con,
        """
        SELECT segment, median(first_days) AS median_days_to_first_permit,
               quantile_cont(first_days, 0.25) AS p25, quantile_cont(first_days, 0.75) AS p75
        FROM s_win WHERE win = 'post' AND first_days IS NOT NULL
          AND segment IN ('single-family','2-6 unit flat','apartment 7+','commercial/industrial')
        GROUP BY 1 ORDER BY 1
    """,
    )
    volume = one(
        con,
        """
        SELECT round(count(*) / 52.0) AS chicago_sales_per_week_2024
        FROM s WHERE sale_date BETWEEN DATE '2024-01-01' AND DATE '2024-12-31'
    """,
    )
    return {"rates": rows, "timing": timing, "trades": trades, "volume": volume}


# --------------------------------------------------------------------------------------------------
# BT3: building violation -> matching repair permit at the same address
# --------------------------------------------------------------------------------------------------
def bt_violation(con) -> dict:
    vt = ["roofing", "masonry", "porch", "windows_doors", "electrical", "plumbing", "hvac", "elevator"]
    parts = []
    for t in vt:
        parts.append(f"""
            SELECT address_key, '{t}' AS trade, violation_date, inspection_category
            FROM violations WHERE t_{t} AND violation_date BETWEEN DATE '2012-01-01' AND DATE '2025-10-31'
        """)
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE v_all AS {" UNION ALL ".join(parts)}
    """)
    # Episodes: first violation of a trade at an address with none of that trade in the previous 365 days
    con.execute("""
        CREATE OR REPLACE TEMP TABLE v_ep AS
        SELECT * FROM (
          SELECT address_key, trade, violation_date, inspection_category,
                 lag(violation_date) OVER (PARTITION BY address_key, trade ORDER BY violation_date) AS prev
          FROM (SELECT address_key, trade, violation_date, min(inspection_category) AS inspection_category
                FROM v_all GROUP BY ALL)
        ) WHERE prev IS NULL OR violation_date - prev > 365
    """)
    case = " ".join(f"WHEN '{t}' THEN p.t_{t}" for t in vt)
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE v_out AS
        SELECT e.address_key, e.trade, e.violation_date, e.inspection_category,
          min(p.issue_date - e.violation_date) FILTER (
              WHERE p.issue_date > e.violation_date AND p.issue_date <= e.violation_date + INTERVAL 365 DAY)
              AS days_to_permit,
          bool_or(p.issue_date > e.violation_date - INTERVAL 730 DAY
              AND p.issue_date <= e.violation_date - INTERVAL 365 DAY) AS pre_permit
        FROM v_ep e
        LEFT JOIN p ON p.address_key = e.address_key AND (CASE e.trade {case} END)
          AND p.issue_date > e.violation_date - INTERVAL 730 DAY
          AND p.issue_date <= e.violation_date + INTERVAL 365 DAY
        GROUP BY ALL
    """)
    rates = q(
        con,
        """
        SELECT trade, count(*) AS episodes,
          round(count(*) / (14 * 52.0), 1) AS episodes_per_week,
          avg(coalesce(days_to_permit <= 90, false)::INT) AS permit_90d,
          avg(coalesce(days_to_permit <= 180, false)::INT) AS permit_180d,
          avg((days_to_permit IS NOT NULL)::INT) AS permit_365d,
          avg(coalesce(pre_permit, false)::INT) AS baseline_same_address_prior_year,
          median(days_to_permit) AS median_days_to_permit
        FROM v_out GROUP BY trade ORDER BY episodes DESC
    """,
    )
    by_category = q(
        con,
        """
        SELECT trade, inspection_category, count(*) AS episodes,
               avg((days_to_permit IS NOT NULL)::INT) AS permit_365d
        FROM v_out WHERE inspection_category IN ('COMPLAINT', 'PERIODIC', 'PERMIT')
          AND trade IN ('porch', 'masonry', 'roofing', 'windows_doors')
        GROUP BY ALL ORDER BY trade, episodes DESC
    """,
    )
    # Market structure: who pulls the permits that follow violations (porch + masonry), last 3 years
    winners = q(
        con,
        f"""
        WITH f AS (
          SELECT DISTINCT p.id, e.trade FROM v_ep e JOIN p ON p.address_key = e.address_key
            AND (CASE e.trade {case} END)
            AND p.issue_date > e.violation_date AND p.issue_date <= e.violation_date + INTERVAL 365 DAY
          WHERE e.trade IN ('porch', 'masonry') AND e.violation_date >= DATE '2022-01-01'
        )
        SELECT f.trade, pp.name_key AS contractor, count(*) AS permits
        FROM f JOIN permit_parties pp ON pp.permit_id = f.id
        WHERE pp.role IN ('gc', 'masonry') AND pp.name_key <> ''
        GROUP BY f.trade, pp.name_key QUALIFY row_number() OVER (PARTITION BY f.trade ORDER BY count(*) DESC) <= 5
        ORDER BY f.trade, permits DESC
    """,
    )
    return {"rates": rates, "by_category": by_category, "winners": winners}


# --------------------------------------------------------------------------------------------------
# BT4: GC "open door" — does a GC's past sub rotation predict a new sub on its next job?
# --------------------------------------------------------------------------------------------------
def bt_rotation(con) -> dict:
    out = {}
    for trade in ("electrical", "plumbing", "hvac"):
        con.execute(f"""
            CREATE OR REPLACE TEMP TABLE jobs AS
            WITH major AS (SELECT id, issue_date FROM p WHERE {MAJOR}),
            gc AS (SELECT permit_id, min(name_key) AS gc FROM permit_parties
                   WHERE role = 'gc' AND name_key <> '' GROUP BY permit_id),
            sub AS (SELECT permit_id, min(name_key) AS sub FROM permit_parties
                    WHERE role = '{trade}' AND name_key <> '' GROUP BY permit_id)
            SELECT m.id, m.issue_date, gc.gc, sub.sub FROM major m
            JOIN gc ON gc.permit_id = m.id JOIN sub ON sub.permit_id = m.id
        """)
        con.execute("""
            CREATE OR REPLACE TEMP TABLE seq AS
            WITH j AS (
              SELECT jobs.*, row_number() OVER (PARTITION BY gc ORDER BY issue_date, id) AS k,
                     row_number() OVER (PARTITION BY gc, sub ORDER BY issue_date, id) = 1 AS is_new
              FROM jobs
            )
            SELECT *,
              -- prior novelty rate excluding the GC's first job (always "new")
              (sum(is_new::INT) OVER w - 1) / nullif(k - 2, 0) AS prior_rate,
              k - 1 AS prior_jobs
            FROM j
            WINDOW w AS (PARTITION BY gc ORDER BY issue_date, id ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING)
        """)
        test = "issue_date >= DATE '2022-01-01' AND prior_jobs >= 5"
        base = one(con, f"SELECT count(*) AS test_jobs, avg(is_new::INT) AS base_rate FROM seq WHERE {test}")
        buckets = q(
            con,
            f"""
            SELECT ntile(5) OVER (ORDER BY prior_rate, id) AS quintile, prior_rate, is_new FROM seq WHERE {test}
        """,
        )
        agg: dict[int, list] = {}
        for b in buckets:
            agg.setdefault(b["quintile"], []).append(b)
        quint = [
            {
                "quintile": k,
                "prior_rate_range": f"{min(x['prior_rate'] for x in v):.2f}–{max(x['prior_rate'] for x in v):.2f}",
                "jobs": len(v),
                "observed_new_sub_rate": sum(x["is_new"] for x in v) / len(v),
            }
            for k, v in sorted(agg.items())
        ]
        out[trade] = {"base": base, "quintiles": quint}
    return out


# --------------------------------------------------------------------------------------------------
# BT5: restaurant build-out permit -> retail food license at the same address
# --------------------------------------------------------------------------------------------------
def bt_restaurant(con) -> dict:
    con.execute(r"""
        CREATE OR REPLACE TEMP TABLE rp AS
        SELECT address_key, min(application_date) AS permit_app, min(issue_date) AS permit_issue
        FROM p
        WHERE regexp_matches(description, '\bRESTAURANT|KITCHEN HOOD|\bHOOD AND DUCT|FOOD SERVICE|\bCAFE\b|COFFEE SHOP|\bBAKERY|\bTAVERN|\bPIZZ')
          AND permit_type IN ('PERMIT - RENOVATION/ALTERATION', 'PERMIT - NEW CONSTRUCTION',
                              'PERMIT - EXPRESS PERMIT PROGRAM', 'PERMIT - EASY PERMIT PROCESS')
          AND issue_date BETWEEN DATE '2012-01-01' AND DATE '2025-06-30'
        GROUP BY address_key, year(issue_date)
    """)
    summary = one(
        con,
        """
        SELECT count(*) AS restaurant_permits,
          avg((EXISTS (SELECT 1 FROM food_licenses f WHERE f.address_key = rp.address_key
               AND f.application_date BETWEEN rp.permit_issue - INTERVAL 30 DAY
                                          AND rp.permit_issue + INTERVAL 365 DAY))::INT) AS license_within_1y
        FROM rp
    """,
    )
    timing = one(
        con,
        """
        WITH m AS (
          SELECT rp.*, min(f.application_date) AS lic_app, min(f.issue_date) AS lic_issue
          FROM rp JOIN food_licenses f ON f.address_key = rp.address_key
           AND f.application_date BETWEEN rp.permit_issue - INTERVAL 30 DAY AND rp.permit_issue + INTERVAL 365 DAY
          GROUP BY ALL
        )
        SELECT count(*) AS matched,
          median(lic_app - permit_issue) AS median_days_permit_issue_to_license_application,
          median(lic_issue - permit_issue) AS median_days_permit_issue_to_license_issue,
          median(lic_issue - permit_app) AS median_days_permit_application_to_license_issue
        FROM m
    """,
    )
    recall = one(
        con,
        """
        SELECT count(*) AS new_food_licenses_2013_2025,
          avg((EXISTS (SELECT 1 FROM rp WHERE rp.address_key = f.address_key
               AND rp.permit_issue BETWEEN f.application_date - INTERVAL 365 DAY
                                       AND f.application_date + INTERVAL 30 DAY))::INT)
            AS share_preceded_by_restaurant_permit
        FROM food_licenses f WHERE f.application_date BETWEEN DATE '2013-01-01' AND DATE '2025-06-30'
    """,
    )
    return {"summary": summary, "timing": timing, "recall": recall}


# --------------------------------------------------------------------------------------------------
# BT6: composite parcel score — naive-Bayes combination of signals, trained 2016-2019, tested 2022-2024
# --------------------------------------------------------------------------------------------------
def bt_composite(con) -> dict:
    build_parcel_features(
        con,
        "SELECT unnest(generate_series(DATE '2016-01-01', DATE '2024-07-01', INTERVAL 6 MONTH))::DATE AS d",
    )
    train = "d BETWEEN DATE '2016-01-01' AND DATE '2019-07-01'"
    test = "d BETWEEN DATE '2022-01-01' AND DATE '2024-07-01'"
    prior = one(con, f"SELECT avg(y::INT) AS base_rate, count(*) AS rows FROM feat WHERE {train}")
    # Likelihood ratios with Laplace smoothing
    weights = []
    for f, label in FEATURES.items():
        r = one(
            con,
            f"""
            SELECT
              (count(*) FILTER (WHERE y AND {f}) + 1.0) / (count(*) FILTER (WHERE y) + 2.0) AS p_f_y,
              (count(*) FILTER (WHERE NOT y AND {f}) + 1.0) / (count(*) FILTER (WHERE NOT y) + 2.0) AS p_f_n,
              avg(y::INT) FILTER (WHERE {f}) AS rate_if_present,
              count(*) FILTER (WHERE {f}) AS n_present
            FROM feat WHERE {train}
        """,
        )
        w_on = math.log(r["p_f_y"] / r["p_f_n"])
        w_off = math.log((1 - r["p_f_y"]) / (1 - r["p_f_n"]))
        weights.append(
            {
                "feature": f,
                "label": label,
                "w_present": w_on,
                "w_absent": w_off,
                "train_rate_if_present": r["rate_if_present"],
                "lift_if_present": (r["rate_if_present"] or 0) / prior["base_rate"],
                "n_present": r["n_present"],
            }
        )
    score = " + ".join(
        f"(CASE WHEN {w['feature']} THEN {w['w_present']} ELSE {w['w_absent']} END)" for w in weights
    )
    con.execute(
        f"CREATE OR REPLACE TEMP TABLE scored AS SELECT d, pin10, y, {score} AS s FROM feat WHERE {test}"
    )
    test_base = one(
        con, "SELECT avg(y::INT) AS base_rate, count(*) AS rows, count(DISTINCT d) AS snapshots FROM scored"
    )
    at_k = []
    for k in (100, 500, 2000):
        r = one(
            con,
            f"""
            SELECT avg(y::INT) AS precision FROM (
              SELECT y, row_number() OVER (PARTITION BY d ORDER BY s DESC, hash(pin10)) AS rk FROM scored
            ) WHERE rk <= {k}
        """,
        )
        at_k.append(
            {
                "k_per_snapshot": k,
                "precision": r["precision"],
                "lift_vs_base": r["precision"] / test_base["base_rate"],
            }
        )
    best_single = one(
        con,
        f"""
        SELECT avg(y::INT) AS precision_demo_only FROM feat WHERE {test} AND demo_365
    """,
    )

    # Combination model: empirical conversion rate of each exact signal combination in training years,
    # shrunk toward the base rate (m pseudo-observations). Handles correlated signals that naive Bayes
    # double-counts, and every score is a directly explainable historical rate.
    cols = ", ".join(FEATURES)
    fit_combo_rates(con, train)
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE scored_combo AS
        SELECT f.d, f.pin10, f.y, coalesce(c.rate, {prior["base_rate"]}) AS s
        FROM feat f LEFT JOIN combo c USING ({cols}) WHERE f.{test}
    """)
    at_k_combo = []
    for k in (100, 500, 2000, 10000):
        r = one(
            con,
            f"""
            SELECT avg(y::INT) AS precision FROM (
              SELECT y, row_number() OVER (PARTITION BY d ORDER BY s DESC, hash(pin10)) AS rk FROM scored_combo
            ) WHERE rk <= {k}
        """,
        )
        at_k_combo.append(
            {
                "k_per_snapshot": k,
                "precision": r["precision"],
                "lift_vs_base": r["precision"] / test_base["base_rate"],
            }
        )
    top_combos = q(
        con,
        f"""
        SELECT c.*, t.test_n, t.test_rate FROM combo c
        JOIN (SELECT {cols}, count(*) AS test_n, avg(y::INT) AS test_rate FROM feat WHERE {test} GROUP BY ALL) t
          USING ({cols})
        WHERE c.n >= 300 ORDER BY c.rate DESC LIMIT 12
    """,
    )
    return {
        "train_base": prior,
        "weights": weights,
        "test_base": test_base,
        "precision_at_k": at_k,
        "best_single_signal": best_single,
        "precision_at_k_combo": at_k_combo,
        "top_combos": top_combos,
    }


# --------------------------------------------------------------------------------------------------
# BT7: 311 lead types (re-validation of signal-lab H07-H09, same within-property method)
# --------------------------------------------------------------------------------------------------
BT7_SPECS = [
    {
        "key": "complaint",
        "label": "'Building Violation' 311 complaint → building violation",
        "signal": "SELECT address_key AS k, created_date AS d FROM sr311 "
        "WHERE sr_type = 'Building Violation' AND NOT duplicate",
        "target": "SELECT address_key AS k, violation_date AS d FROM violations",
        "window": 120,
        "start": "2016-01-01",
        "end": "2025-10-31",
        "key_name": "address",
    },
    {
        "key": "porch_request",
        "label": "'Porch Inspection Request' 311 call → porch permit",
        "signal": "SELECT address_key AS k, created_date AS d FROM sr311 "
        "WHERE sr_type = 'Porch Inspection Request' AND NOT duplicate",
        "target": "SELECT address_key AS k, issue_date AS d FROM p WHERE t_porch",
        "window": 365,
        "start": "2016-01-01",
        "end": "2025-10-31",
        "key_name": "address",
    },
    {
        "key": "vacant",
        "label": "'Vacant/Abandoned Building Complaint' → property sale",
        "signal": "SELECT a.pin10 AS k, s.created_date AS d FROM sr311 s JOIN addr_pin a USING (address_key) "
        "WHERE s.sr_type = 'Vacant/Abandoned Building Complaint' AND NOT s.duplicate",
        "target": "SELECT pin10 AS k, sale_date AS d FROM sales WHERE NOT filtered_out",
        "window": 365,
        "start": "2016-01-01",
        "end": "2025-06-30",
        "key_name": "parcel (pin10)",
    },
]


def same_property(con, spec: dict) -> dict:
    """One episode per key per window (signals within the window of the previous one are dropped).

    conversion = share of episodes followed by the target within the window; baseline = share of the same keys
    that already had the target in the equally long window before the episode; lift = conversion / baseline.
    """
    window, start, end = spec["window"], spec["start"], spec["end"]
    con.execute(f"CREATE OR REPLACE TEMP TABLE sig AS {spec['signal']}")
    con.execute(f"CREATE OR REPLACE TEMP TABLE tgt AS {spec['target']}")
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
          count(*) FILTER (WHERE d > DATE '{end}' - INTERVAL 365 DAY) / 52.0 AS signals_per_week,
          min(d) AS first_signal, max(d) AS last_signal
        FROM o
    """,
    )
    r["lift"] = r["conversion"] / r["baseline"] if r["baseline"] else None
    r["by_year"] = q(
        con,
        f"""
        SELECT year(e.d) AS year, count(*) AS signals,
          avg((EXISTS (SELECT 1 FROM tgt t WHERE t.k = e.k AND t.d > e.d AND t.d <= e.d + INTERVAL {window} DAY))::INT)
            AS conversion
        FROM ep e GROUP BY 1 ORDER BY 1
    """,
    )
    r["window_days"] = window
    r["period"] = f"{start} to {end}"
    r["key"] = spec["key_name"]
    r["label"] = spec["label"]
    return {k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()}


def bt_311(con) -> dict:
    return {spec["key"]: same_property(con, spec) for spec in BT7_SPECS}


# --------------------------------------------------------------------------------------------------
# BT0: market sizing for owner-facing trades (who would buy marketing / leads)
# --------------------------------------------------------------------------------------------------
def bt_market(con) -> dict:
    # Which permit role identifies the contractor doing the work. Roofers, porch builders, window and
    # solar installers file as "general contractor" on their own small permits.
    trade_roles = {
        "roofing": "'gc'",
        "porch": "'gc'",
        "windows_doors": "'gc'",
        "solar": "'gc'",
        "fence": "'gc'",
        "garage": "'gc'",
        "concrete_flatwork": "'gc', 'masonry'",
        "masonry": "'masonry'",
        "hvac": "'hvac'",
        "plumbing": "'plumbing'",
        "electrical": "'electrical'",
    }
    rows = []
    for t, roles in trade_roles.items():
        r = one(
            con,
            f"""
            WITH x AS (
              SELECT id, reported_cost FROM p
              WHERE t_{t} AND issue_date > (SELECT max(issue_date) FROM p) - INTERVAL 365 DAY
                AND NOT {MAJOR}
            ),
            c AS (
              SELECT pp.name_key, count(DISTINCT pp.permit_id) AS jobs
              FROM permit_parties pp JOIN x ON x.id = pp.permit_id
              WHERE pp.role IN ({roles}) AND pp.name_key <> '' GROUP BY 1
            )
            SELECT '{t}' AS trade, (SELECT count(*) FROM x) AS permits_last_12m,
              (SELECT median(reported_cost) FROM x WHERE reported_cost > 0) AS median_reported_cost,
              (SELECT count(*) FROM c) AS distinct_contractors,
              (SELECT count(*) FROM c WHERE jobs >= 5) AS contractors_5plus_jobs,
              (SELECT sum(jobs) FROM (SELECT jobs FROM c ORDER BY jobs DESC LIMIT 10))
                / nullif((SELECT sum(jobs) FROM c), 0) AS top10_share
        """,
        )
        rows.append(r)
    return {"rows": rows}


# --------------------------------------------------------------------------------------------------
def pct(x) -> str:
    return "—" if x is None else f"{100 * x:.1f}%"


def render(r: dict) -> str:
    L: list[str] = []
    a = L.append
    a(f"# Lead-signal backtests — {r['generated_on']}")
    a("")
    a(
        "Source: City of Chicago permits (2006–present), building violations (2010–present), retail food "
        "licenses; Cook County Assessor parcel sales (Chicago townships, 2010–present). Reproduce with "
        "`uv run python research/backtests/run_backtests.py` after building the warehouse."
    )
    a("")
    a(
        "Reading guide: **conversion** = share of signals followed by the target event in the window; "
        "**baseline** = the same properties' rate in an earlier, signal-free window; **lift** = conversion ÷ "
        "baseline. Permits only capture *permitted* work, so all conversion rates are lower bounds on real jobs."
    )

    d = r["demolition"]
    s = d["summary"]
    a("\n## BT1 — Demolition permit → new construction on the same property\n")
    a(
        f"- Demolitions tested (2010–Oct 2024): **{s['demolitions']:,}**; ~{d['volume']['demolitions_per_week_last_year']} per week last year"
    )
    a(f"- New-construction permit issued within 2 years: **{pct(s['nc_within_2y'])}**")
    a(
        f"- …and the new-construction application was filed *after* the demolition permit: **{pct(s['nc_applied_after_demo'])}** of demolitions"
    )
    a(
        f"- Median days demolition → new-construction application: **{s['median_days_demo_to_nc_application']}**; → issue: **{s['median_days_demo_to_nc_issue']}** (p25 {s['p25_days_to_nc_issue']:.0f}, p75 {s['p75_days_to_nc_issue']:.0f})"
    )
    a(f"- Median reported cost of the follow-on new construction: ${s['median_nc_reported_cost']:,.0f}")
    a(
        f"- Demolitions with *no* new-construction permit within 60 days: {s['demolitions_without_nc_within_60d']:,}; of these, new construction issued 61–730 days later: **{pct(s['later_nc_61_730d'])}**"
    )
    a(
        f"- Recall: **{pct(d['recall']['share_preceded_by_demo'])}** of {d['recall']['nc_permits_2012_2026']:,} new-construction permits (2012–2026) had a demolition permit at the property in the 2 years before their application"
    )
    a("\nParties named on the follow-on new-construction permits:\n")
    a("| Role | Share of follow-on permits naming it |\n| --- | --- |")
    for x in d["roles_on_followon_nc"]:
        a(f"| {x['role']} | {pct(x['share_named'])} |")
    a("\n| Year | Demolitions | New construction within 2y |\n| --- | --- | --- |")
    for x in d["by_year"]:
        a(f"| {x['year']} | {x['demolitions']:,} | {pct(x['nc_within_2y'])} |")

    sa = r["sale"]
    a("\n## BT2 — Property sale → permits in the following 12 months\n")
    a(
        f"Chicago arm's-length single-parcel sales, 2012–mid 2025 (~{sa['volume']['chicago_sales_per_week_2024']:,.0f} sales/week in 2024). "
        "Post = 12 months after sale; baseline = months 13–24 *before* the sale at the same parcel.\n"
    )
    head = "| Segment | Sales | " + " | ".join(t for t in sa["trades"]) + " |"
    a("Each cell: post-sale rate (lift vs baseline).\n")
    a(head)
    a("| --- | --- | " + " | ".join("---" for _ in sa["trades"]) + " |")
    for row in sa["rates"]:
        cells = []
        for t in sa["trades"]:
            post, pre = row[f"post_{t}"], row[f"pre_{t}"]
            lift = f"{post / pre:.1f}x" if pre else "n/a"
            cells.append(f"{pct(post)} ({lift})")
        a(f"| {row['segment']} | {row['sales']:,} | " + " | ".join(cells) + " |")
    a("\n| Segment | Median days sale → first permit | p25 | p75 |\n| --- | --- | --- | --- |")
    for x in sa["timing"]:
        a(f"| {x['segment']} | {x['median_days_to_first_permit']} | {x['p25']:.0f} | {x['p75']:.0f} |")

    v = r["violation"]
    a("\n## BT3 — Building violation → matching repair permit at the same address\n")
    a("Episodes = first violation of that trade at an address with none in the prior year (2012–Oct 2025).\n")
    a(
        "| Trade | Episodes | Per week | Permit ≤90d | ≤180d | ≤365d | Baseline (prior year) | Lift | Median days |"
    )
    a("| --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for x in v["rates"]:
        lift = (
            f"{x['permit_365d'] / x['baseline_same_address_prior_year']:.1f}x"
            if x["baseline_same_address_prior_year"]
            else "n/a"
        )
        a(
            f"| {x['trade']} | {x['episodes']:,} | {x['episodes_per_week']} | {pct(x['permit_90d'])} | {pct(x['permit_180d'])} | "
            f"{pct(x['permit_365d'])} | {pct(x['baseline_same_address_prior_year'])} | {lift} | {x['median_days_to_permit']} |"
        )
    a("\n| Trade | Inspection category | Episodes | Permit ≤365d |\n| --- | --- | --- | --- |")
    for x in v["by_category"]:
        a(f"| {x['trade']} | {x['inspection_category']} | {x['episodes']:,} | {pct(x['permit_365d'])} |")
    a("\nTop contractors on permits that followed porch/masonry violations (2022+):\n")
    a("| Trade | Contractor | Permits |\n| --- | --- | --- |")
    for x in v["winners"]:
        a(f"| {x['trade']} | {x['contractor']} | {x['permits']} |")

    a("\n## BT4 — GC “open door”: does past sub rotation predict a new sub on the next job?\n")
    a(
        "Major permits (new construction/renovation ≥ $100k). Feature = share of a GC's prior jobs that used a sub "
        "new to that GC. Tested on jobs from 2022 on, GCs with ≥5 prior jobs.\n"
    )
    for trade, x in r["rotation"].items():
        a(
            f"**{trade}** — {x['base']['test_jobs']:,} test jobs; base rate of a new sub: {pct(x['base']['base_rate'])}\n"
        )
        a(
            "| Quintile of prior rotation | Prior-rate range | Jobs | Observed new-sub rate |\n| --- | --- | --- | --- |"
        )
        for qn in x["quintiles"]:
            a(
                f"| {qn['quintile']} | {qn['prior_rate_range']} | {qn['jobs']:,} | {pct(qn['observed_new_sub_rate'])} |"
            )
        a("")

    rs = r["restaurant"]
    a("## BT5 — Restaurant build-out permit → retail food license at the same address\n")
    a(
        f"- Restaurant-related permits (2012–mid 2025): **{rs['summary']['restaurant_permits']:,}**; followed by a new retail food license application within a year: **{pct(rs['summary']['license_within_1y'])}**"
    )
    t = rs["timing"]
    a(
        f"- Median days permit issue → license application: **{t['median_days_permit_issue_to_license_application']}**; → license issue: **{t['median_days_permit_issue_to_license_issue']}**; permit *application* → license issue: **{t['median_days_permit_application_to_license_issue']}**"
    )
    a(
        f"- Recall: **{pct(rs['recall']['share_preceded_by_restaurant_permit'])}** of {rs['recall']['new_food_licenses_2013_2025']:,} new food licenses had a restaurant-related permit at the address in the prior year"
    )

    c = r["composite"]
    a("\n## BT6 — Composite parcel score (naive Bayes), trained 2016–2019, tested 2022–2024\n")
    a(
        f"Target: a major permit (new construction or renovation ≥ $100k) *applied for* at the parcel within 180 days of the snapshot. "
        f"Universe: {c['test_base']['rows'] // c['test_base']['snapshots']:,} Chicago parcels per snapshot; test base rate {pct(c['test_base']['base_rate'])}.\n"
    )
    a(
        "| Signal | Weight if present | Train rate if present | Lift | Parcels with signal (train) |\n| --- | --- | --- | --- | --- |"
    )
    for w in c["weights"]:
        a(
            f"| {w['label']} | {w['w_present']:+.2f} | {pct(w['train_rate_if_present'])} | {w['lift_if_present']:.1f}x | {w['n_present']:,} |"
        )
    a("\nPrecision of the top-K parcels per half-year snapshot (test years):\n")
    a(
        "| Top-K per snapshot | ≈ per week | Naive Bayes precision | Combination-model precision | Combination lift |"
    )
    a("| --- | --- | --- | --- | --- |")
    nb = {x["k_per_snapshot"]: x for x in c["precision_at_k"]}
    for x in c["precision_at_k_combo"]:
        k = x["k_per_snapshot"]
        nbp = pct(nb[k]["precision"]) if k in nb else "—"
        a(f"| {k:,} | {k / 26:.0f} | {nbp} | {pct(x['precision'])} | {x['lift_vs_base']:.0f}x |")
    a(
        f"\nBest single signal (demolition in last 365d) precision on test: {pct(c['best_single_signal']['precision_demo_only'])}."
    )
    a("\nHighest-converting signal combinations (train rate, then out-of-sample test rate):\n")
    a(
        "| Signals present | Train parcels | Train rate | Test parcels | Test rate |\n| --- | --- | --- | --- | --- |"
    )
    for x in c["top_combos"]:
        present = ", ".join(FEATURES[f] for f in FEATURES if x[f]) or "(none)"
        a(f"| {present} | {x['n']:,} | {pct(x['rate'])} | {x['test_n']:,} | {pct(x['test_rate'])} |")

    t7 = r["sr311"]
    a("\n## BT7 — 311 lead types (re-validation of signal-lab H07–H09)\n")
    a(
        "Same within-property method as the signal lab: one episode per key per window; **baseline** = share of the "
        "same keys that already had the target in the equally long window *before* the signal. 311 data starts "
        "mid-2018, so these cover 2018 onward. Duplicates are excluded.\n"
    )
    a(
        "| Signal → target | Key | Window | Signals | Conversion | Baseline | Lift | Median days | Signals/week (last year) |"
    )
    a("| --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for x in t7.values():
        lift = f"{x['lift']:.1f}x" if x["lift"] else "n/a"
        a(
            f"| {x['label']} | {x['key']} | {x['window_days']}d | {x['signals']:,} | {pct(x['conversion'])} | "
            f"{pct(x['baseline'])} | {lift} | {x['median_days']} | {x['signals_per_week']:.1f} |"
        )
    a("\nConversion by year of the signal (signals / conversion within the window):\n")
    a(
        "| Year | "
        + " | ".join(f"{x['label'].split(' → ')[0]} (signals / conversion)" for x in t7.values())
        + " |"
    )
    a("| --- | " + " | ".join("---" for _ in t7) + " |")
    years = sorted({y["year"] for x in t7.values() for y in x["by_year"]})
    for yr in years:
        cells = []
        for x in t7.values():
            row = next((y for y in x["by_year"] if y["year"] == yr), None)
            cells.append(f"{row['signals']:,} / {pct(row['conversion'])}" if row else "—")
        a(f"| {yr} | " + " | ".join(cells) + " |")

    a(
        "\n## BT0 — Market size: contractors active in owner-facing trades (last 12 months, non-major permits)\n"
    )
    a("| Trade | Permits | Median reported cost | Distinct contractors | With 5+ jobs | Top-10 share |")
    a("| --- | --- | --- | --- | --- | --- |")
    for x in r["market"]["rows"]:
        cost = f"${x['median_reported_cost']:,.0f}" if x["median_reported_cost"] else "—"
        a(
            f"| {x['trade']} | {x['permits_last_12m']:,} | {cost} | {x['distinct_contractors']:,} | "
            f"{x['contractors_5plus_jobs']:,} | {pct(x['top10_share'])} |"
        )
    a("")
    return "\n".join(L)


def main() -> int:
    if not DB.exists():
        print("warehouse missing: run `uv run python -m engine.warehouse sync && ... build` first")
        return 1
    con = duckdb.connect(str(DB), read_only=True)
    con.execute("SET memory_limit = '8GB'")
    prepare_base(con)
    results = {"generated_on": date.today().isoformat()}
    backtests = [
        ("demolition", bt_demolition),
        ("sale", bt_sale),
        ("violation", bt_violation),
        ("rotation", bt_rotation),
        ("restaurant", bt_restaurant),
        ("composite", bt_composite),
        ("sr311", bt_311),
        ("market", bt_market),
    ]
    full = len(sys.argv) <= 1
    for name, fn in backtests:
        if not full and name not in sys.argv[1:]:
            continue
        print(f"running {name} ...", flush=True)
        results[name] = fn(con)
    OUT.mkdir(parents=True, exist_ok=True)
    stem = OUT / f"backtests-{results['generated_on']}"
    json_path = stem.with_suffix(".json") if full else stem.with_suffix(".partial.json")
    json_path.write_text(json.dumps(results, indent=2, default=str))
    if full:
        stem.with_suffix(".md").write_text(render(results))
    print(f"wrote {json_path}" + (" and .md" if full else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
