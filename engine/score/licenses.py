"""Business-license and big-permit signals (signal lab H33 and H29), shared by the snapshot and the backtests.

Definitions are copied from research/signal_lab/lab.py (`h33_buildout_permit_to_new_license`,
`h29_trades_after_big_permit` and the license-site helpers they use), parameterized by period, so the formula that
was validated historically is exactly the formula that scores the live lists. The equivalence with the lab is checked
by calling both on the same warehouse (see the handoff).

Requires the warehouse tables `permits`, `permit_parties`, `sales`, `res_chars`, `biz_license_history` and the base
temp tables `p` and `addr_pin` from `engine.score.signals.prepare_base`. Every temp table made here is prefixed
`lc_`, so it never collides with the snapshot's or the lab's own. Floats are returned unrounded.
"""

from __future__ import annotations

from datetime import date, timedelta

from engine.score.food import RENO_PREDICATE
from engine.score.signals import one, q

R4_START = "2016-01-01"
BUCKET_RESIDENTIAL = "single-family/other residential (2xx)"
BUCKET_UNKNOWN = "unknown class"
BUCKET_VACANT = "vacant land (1xx)"


def class_bucket_sql(cls: str) -> str:
    return f"""CASE
      WHEN {cls} IS NULL THEN '{BUCKET_UNKNOWN}'
      WHEN left({cls}, 1) = '5' THEN 'commercial/industrial (5xx)'
      WHEN left({cls}, 1) = '3' THEN 'multifamily 7+ (3xx)'
      WHEN {cls} = '211' THEN '2-6 unit flats (211)'
      WHEN {cls} = '212' THEN 'mixed-use up to 6 units (212)'
      WHEN left({cls}, 1) = '2' THEN '{BUCKET_RESIDENTIAL}'
      WHEN left({cls}, 1) = '1' THEN '{BUCKET_VACANT}'
      ELSE 'exempt/other' END"""


def ensure_classes(con) -> None:
    """Temp tables lc_addr_map, lc_pin_class, lc_addr_cls (address -> parcel class bucket) and lc_ctr (contractors)."""
    if con.execute("SELECT count(*) FROM duckdb_tables() WHERE table_name = 'lc_classes_ready'").fetchone()[
        0
    ]:
        return
    con.execute("""
        CREATE OR REPLACE TEMP TABLE lc_addr_map AS
        SELECT address_key, first(pin10 ORDER BY pri, pin10) AS pin10 FROM (
          SELECT address_key, pin10, 0 AS pri FROM addr_pin
          UNION ALL SELECT address_key, pin10, 1 FROM parcels WHERE address_key IS NOT NULL AND pin10 IS NOT NULL
        ) GROUP BY address_key
    """)
    con.execute("""
        CREATE OR REPLACE TEMP TABLE lc_pin_class AS
        SELECT pin10, coalesce(rc.class, s.cls) AS cls FROM (
          SELECT pin10, first(class ORDER BY sale_date DESC, pin) AS cls FROM sales
          WHERE class IS NOT NULL GROUP BY pin10
        ) s FULL JOIN (SELECT pin10, class FROM res_chars) rc USING (pin10)
    """)
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE lc_addr_cls AS
        SELECT m.address_key, m.pin10, c.cls, {class_bucket_sql("c.cls")} AS bucket
        FROM lc_addr_map m LEFT JOIN lc_pin_class c USING (pin10)
    """)
    con.execute("""
        CREATE OR REPLACE TEMP TABLE lc_ctr AS
        SELECT DISTINCT permit_id, name_key FROM permit_parties
        WHERE name_key <> '' AND ((role NOT IN ('owner', 'owner_gc', 'architect', 'engineer', 'expediter', 'other'))
              OR role_raw LIKE '%CONTRACTOR%')
    """)
    con.execute("CREATE OR REPLACE TEMP TABLE lc_classes_ready AS SELECT 1 AS x")


# --- business licenses ------------------------------------------------------------------------------------
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
GROUP_PRIORITY = {
    "auto": 1,
    "food & drink": 2,
    "personal services/beauty": 3,
    "health/fitness/childcare": 4,
    "retail": 5,
    "other": 6,
}


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


def row_end(alias: str, d: str) -> str:
    """End date of a license row as known on date d: cancellations count only once they have happened."""
    return (
        f"CASE WHEN {alias}.status IN ('AAC', 'REV') AND {alias}.status_change_date <= {d} "
        f"THEN least({alias}.status_change_date, {alias}.exp_eff) ELSE {alias}.exp_eff END"
    )


def ensure_licenses(con) -> None:
    """Temp tables lc_licp (premises licenses with group), lc_nad (first license of an account at an address) and
    lc_reno (days with a renovation, build-out or new-construction permit per address)."""
    ensure_classes(con)
    if con.execute("SELECT count(*) FROM duckdb_tables() WHERE table_name = 'lc_lic_ready'").fetchone()[0]:
        return
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE lc_licp AS
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
        CREATE OR REPLACE TEMP TABLE lc_nad AS
        WITH first_rec AS (SELECT acct, address_key, min(issue_date) AS first_any FROM lc_licp GROUP BY acct, address_key)
        SELECT l.acct, l.address_key AS k, f.first_any AS d, first(l.grp ORDER BY CASE l.grp {prio} END, l.row_id, l.license_id) AS grp,
          min(l.app_date) AS app_date
        FROM lc_licp l JOIN first_rec f ON f.acct = l.acct AND f.address_key = l.address_key AND l.issue_date = f.first_any
        WHERE l.app = 'ISSUE' GROUP BY l.acct, l.address_key, f.first_any
    """)
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE lc_reno AS
        SELECT DISTINCT address_key AS k, issue_date AS d FROM p WHERE address_key IS NOT NULL AND {RENO_PREDICATE}
    """)
    con.execute("CREATE OR REPLACE TEMP TABLE lc_lic_ready AS SELECT 1 AS x")


def std_rate(rows: list[dict], sig_pred, ctl_pred, min_ctl: int = 5) -> dict:
    """Rate of the control cells standardized to the signal cells' (class, year) mix. rows: grp, yr, cell, n, hits."""
    sig: dict[tuple, list[int]] = {}
    ctl: dict[tuple, list[int]] = {}
    for r in rows:
        key = (r["grp"], r["yr"])
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
        "hits": hits,
        "rate": hits / n if n else None,
        "matched_signals": wsum,
        "matched_rate": sig_rate_matched,
        "control_signals": ctl_n,
        "control_raw_rate": ctl_hits / ctl_n if ctl_n else None,
        "control_std_rate": std,
        "lift": sig_rate_matched / std if std and sig_rate_matched is not None else None,
    }


# --- H33: build-out permit at an unlicensed space -> new business ------------------------------------------
BUCKETS_33 = ("commercial/industrial (5xx)", "mixed-use up to 6 units (212)", "multifamily 7+ (3xx)")
BUCKET_LIST_33 = ", ".join(f"'{b}'" for b in BUCKETS_33)


def build_out_signals_sql(start: str, end: str) -> str:
    """Build-out permit episodes at class-known commercial, mixed-use and 7+ unit addresses with no business license
    in force on the permit date; one per address per 365 days (the lab's H33 signal). Columns: k, d, bucket, cost,
    cost_band, pid (the day's costliest permit). Needs ensure_licenses."""
    return f"""
        SELECT k, d, bucket, cost, pid,
          CASE WHEN cost >= 100000 THEN '$100k+' WHEN cost >= 25000 THEN '$25k-$100k'
               WHEN cost > 0 THEN 'under $25k' ELSE 'no cost reported' END AS cost_band FROM (
          SELECT r.k, r.d, r.cost, r.pid, ac.bucket, lag(r.d) OVER (PARTITION BY r.k ORDER BY r.d) AS prev
          FROM (SELECT address_key AS k, issue_date AS d, max(coalesce(reported_cost, 0)) AS cost,
                  first(id ORDER BY coalesce(reported_cost, 0) DESC, id) AS pid FROM p
                WHERE address_key IS NOT NULL AND {RENO_PREDICATE} GROUP BY 1, 2) r
          JOIN (SELECT DISTINCT address_key, bucket FROM lc_addr_cls WHERE bucket IN ({BUCKET_LIST_33})) ac
            ON ac.address_key = r.k
          WHERE NOT EXISTS (SELECT 1 FROM lc_licp x WHERE x.address_key = r.k AND x.issue_date <= r.d
                            AND {row_end("x", "r.d")} > r.d)
        ) WHERE (prev IS NULL OR d - prev > 365) AND d >= DATE '{start}' AND d <= DATE '{end}'
    """


def new_business(con, *, start: str = R4_START, end: str) -> dict:
    """H33 over build-out permits issued start..end (inclusive). `end` must be at least 365 days before the newest
    license record so every window is complete. Leaves temp tables lc_s33 (signals) and lc_s33_x (with outcomes).

    Returns the headline (vs a matched control with no license in force and no renovation permit within a year
    either side, standardized to the signals' class x year mix, and vs a 'busy' control with some other permit in
    the prior 90 days), timing, by-class/group/cost/year tables, `cells` (for re-slicing by period with
    `std_rate`) and `delays` (sorted days to the first new license, class-agnostic).
    """
    ensure_licenses(con)
    max_issue = one(con, "SELECT max(issue_date) AS d FROM biz_license_history")["d"]
    last_event = f"DATE '{end}'"
    con.execute(f"CREATE OR REPLACE TEMP TABLE lc_s33 AS {build_out_signals_sql(start, end)}")
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE lc_qd AS
        SELECT unnest(generate_series(DATE '{start}', {last_event}, INTERVAL 3 MONTH))::DATE AS q
    """)
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE lc_pool AS
        SELECT a.address_key AS k, lc_qd.q AS d, a.bucket FROM
          (SELECT DISTINCT address_key, bucket FROM lc_addr_cls WHERE bucket IN ({BUCKET_LIST_33})) a CROSS JOIN lc_qd
        WHERE NOT EXISTS (SELECT 1 FROM lc_reno t WHERE t.k = a.address_key
                          AND t.d > lc_qd.q - INTERVAL 365 DAY AND t.d <= lc_qd.q + INTERVAL 365 DAY)
          AND NOT EXISTS (SELECT 1 FROM lc_licp x WHERE x.address_key = a.address_key AND x.issue_date <= lc_qd.q
                          AND {row_end("x", "lc_qd.q")} > lc_qd.q)
    """)
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE lc_poolb AS
        SELECT DISTINCT a.address_key AS k, lc_qd.q AS d, a.bucket FROM
          (SELECT DISTINCT address_key, bucket FROM lc_addr_cls WHERE bucket IN ({BUCKET_LIST_33})) a CROSS JOIN lc_qd
        WHERE EXISTS (SELECT 1 FROM p x WHERE x.address_key = a.address_key AND NOT {RENO_PREDICATE}
                      AND x.issue_date > lc_qd.q - INTERVAL 90 DAY AND x.issue_date <= lc_qd.q)
          AND NOT EXISTS (SELECT 1 FROM lc_reno t WHERE t.k = a.address_key
                          AND t.d > lc_qd.q - INTERVAL 365 DAY AND t.d <= lc_qd.q + INTERVAL 365 DAY)
          AND NOT EXISTS (SELECT 1 FROM lc_licp x WHERE x.address_key = a.address_key AND x.issue_date <= lc_qd.q
                          AND {row_end("x", "lc_qd.q")} > lc_qd.q)
    """)
    for name in ("lc_s33", "lc_pool", "lc_poolb"):
        con.execute(f"""
            CREATE OR REPLACE TEMP TABLE {name}_x AS
            SELECT e.k, e.d, e.bucket, year(e.d) AS yr,
              min(n.d - e.d) FILTER (WHERE n.d > e.d AND n.d <= e.d + INTERVAL 365 DAY) AS days_after,
              first(n.grp ORDER BY n.d, n.acct) FILTER (WHERE n.d > e.d AND n.d <= e.d + INTERVAL 365 DAY) AS first_grp,
              coalesce(bool_or(n.d > e.d - INTERVAL 730 DAY AND n.d <= e.d - INTERVAL 365 DAY), false) AS own_earlier
              {", e.cost_band" if name == "lc_s33" else ""}
            FROM {name} e LEFT JOIN lc_nad n ON n.k = e.k AND n.d > e.d - INTERVAL 730 DAY AND n.d <= e.d + INTERVAL 365 DAY
            GROUP BY e.k, e.d, e.bucket{", e.cost_band" if name == "lc_s33" else ""}
        """)
    rows = []
    for name, src in (("lc_s33_x", "sig"), ("lc_pool_x", "ctl"), ("lc_poolb_x", "busy")):
        cost = "cost_band" if name == "lc_s33_x" else "'-'"
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
    sig_p, ctl_p, busy_p = (
        (lambda r: r["cell"] == "sig"),
        (lambda r: r["cell"] == "ctl"),
        (lambda r: r["cell"] == "busy"),
    )
    head = std_rate(rows, sig_p, ctl_p)
    busy = std_rate(rows, sig_p, busy_p)
    by_cost = []
    for band in ("no cost reported", "under $25k", "$25k-$100k", "$100k+"):
        h = std_rate(rows, lambda r, band=band: r["cell"] == "sig" and r["cost"] == band, ctl_p)
        hb = std_rate(rows, lambda r, band=band: r["cell"] == "sig" and r["cost"] == band, busy_p)
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
    sig_rows = [r for r in rows if r["cell"] == "sig"]
    own = sum(r["own"] for r in sig_rows) / sum(r["n"] for r in sig_rows)
    tm = one(
        con,
        """
        SELECT median(days_after) AS med, quantile_cont(days_after, 0.25) AS p25, quantile_cont(days_after, 0.75) AS p75,
          avg((days_after <= 90)::INT) FILTER (WHERE days_after IS NOT NULL) AS within_90,
          avg((days_after <= 180)::INT) FILTER (WHERE days_after IS NOT NULL) AS within_180,
          avg((days_after > 30)::INT) FILTER (WHERE days_after IS NOT NULL) AS after_30
        FROM lc_s33_x
    """,
    )
    late = one(con, "SELECT count(*) AS n, count(*) FILTER (WHERE days_after > 30) AS hits FROM lc_s33_x")
    by_group = q(
        con,
        """
        SELECT first_grp AS license_group, count(*) AS new_licenses, median(days_after) AS median_days,
          quantile_cont(days_after, 0.25) AS p25_days, quantile_cont(days_after, 0.75) AS p75_days
        FROM lc_s33_x WHERE days_after IS NOT NULL GROUP BY 1 ORDER BY count(*) DESC, 1
    """,
    )
    tot = sum(r["new_licenses"] for r in by_group)
    for r in by_group:
        r["share_of_conversions"] = r["new_licenses"] / tot
    by_class = []
    for b in BUCKETS_33:
        sub = [r for r in rows if r["grp"] == b]
        h = std_rate(sub, sig_p, ctl_p)
        if h["signals"]:
            by_class.append(
                {
                    "class": b,
                    "signals": h["signals"],
                    "new_license_rate": h["rate"],
                    "control_rate": h["control_std_rate"],
                    "lift": h["lift"],
                }
            )
    by_year = []
    for y in sorted({r["yr"] for r in sig_rows}):
        sub = [r for r in rows if r["yr"] == y]
        h = std_rate(sub, sig_p, ctl_p)
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
          JOIN (SELECT DISTINCT address_key FROM lc_addr_cls WHERE bucket IN ({BUCKET_LIST_33})) ac ON ac.address_key = r.k
          WHERE r.d > DATE '{max_issue}' - INTERVAL 365 DAY
            AND NOT EXISTS (SELECT 1 FROM lc_licp x WHERE x.address_key = r.k AND x.issue_date <= r.d
                            AND {row_end("x", "r.d")} > r.d))
    """,
    )["v"]
    delays = [
        r["days_after"]
        for r in q(con, "SELECT days_after FROM lc_s33_x WHERE days_after IS NOT NULL ORDER BY 1")
    ]
    return {
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
        "by_class": by_class,
        "by_cost": by_cost,
        "by_year": by_year,
        "signal_days": [
            (r["yr"], r["days_after"])
            for r in q(con, "SELECT yr, days_after FROM lc_s33_x ORDER BY yr, days_after NULLS LAST")
        ],
        "cells": rows,
        "delays": delays,
        "first_signal": one(con, "SELECT min(d) AS d FROM lc_s33")["d"],
        "last_signal": one(con, "SELECT max(d) AS d FROM lc_s33")["d"],
    }


def summarize_cells(cells: list[dict], year_from: int | None = None, year_to: int | None = None) -> dict:
    """Headline and busy-control views of `new_business` cells restricted to signal years (inclusive)."""
    sub = [
        r
        for r in cells
        if (year_from is None or r["yr"] >= year_from) and (year_to is None or r["yr"] <= year_to)
    ]
    sig_p, ctl_p, busy_p = (
        (lambda r: r["cell"] == "sig"),
        (lambda r: r["cell"] == "ctl"),
        (lambda r: r["cell"] == "busy"),
    )
    head, busy = std_rate(sub, sig_p, ctl_p), std_rate(sub, sig_p, busy_p)
    return {
        "signals": head["signals"],
        "rate": head["rate"],
        "control_rate": head["control_std_rate"],
        "lift": head["lift"],
        "busy_control_rate": busy["control_std_rate"],
        "lift_vs_busy": busy["lift"],
    }


def build_out_current(con, *, asof: date, days: int) -> None:
    """Temp table lc_cur: build-out signals (same definition as H33) issued in the `days` days up to `asof` at
    addresses with no business license of any kind issued since the permit. Columns as `build_out_signals_sql`.
    Earlier permits still count for the one-per-365-days rule."""
    ensure_licenses(con)
    start = asof - timedelta(days=days - 1)
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE lc_cur AS
        SELECT s.* FROM ({build_out_signals_sql(start.isoformat(), asof.isoformat())}) s
        WHERE NOT EXISTS (SELECT 1 FROM lc_licp x WHERE x.address_key = s.k AND x.issue_date > s.d)
    """)


# --- H29: trades still open after a $1M+ permit -------------------------------------------------------------
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
TRADE_LABELS = {
    "signs": "Signs",
    "elevator": "Elevator",
    "electrical": "Electrical",
    "scaffolding": "Scaffolding",
    "plumbing": "Plumbing",
    "hvac": "HVAC / mechanical",
    "fire_alarm": "Fire alarm / sprinkler",
    "roofing": "Roofing",
    "demolition": "Demolition",
    "renovation": "Renovation / build-out",
}
HEADLINE_TRADES = ("signs", "elevator", "electrical")
BUCKETS_29 = (
    "commercial/industrial (5xx)",
    "multifamily 7+ (3xx)",
    "mixed-use up to 6 units (212)",
    "2-6 unit flats (211)",
    "exempt/other",
)
BUCKET_LIST_29 = ", ".join(f"'{b}'" for b in BUCKETS_29)


def _quartiles(col: str) -> str:
    return f"median({col}) AS med, quantile_cont({col}, 0.25) AS p25, quantile_cont({col}, 0.75) AS p75"


def open_trades(con, *, end: str | None = None) -> dict:
    """H29: a $1M+ new-construction or renovation permit (first at the address in 540 days, from 2016) -> which
    follow-on permits come within 540 days and whether their contractors were already on the big permit.

    `end` = last big-permit date counted (default: newest permit minus 540 days, so every window is complete).
    Leaves temp tables lc_sig (big-permit episodes, open-ended), lc_fo (permits with trade flags) and lc_maj_all.
    """
    ensure_classes(con)
    max_issue = one(con, "SELECT max(issue_date) AS d FROM permits")["d"]
    end_sql = f"DATE '{end}'" if end else f"DATE '{max_issue}' - INTERVAL {FOLLOW_WINDOW} DAY"
    flag_cols = ", ".join(f"({pred}) AS f_{name}" for name, (pred, _) in FOLLOW_TRADES.items())
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE lc_fo AS
        SELECT id, address_key AS k, issue_date AS d, {flag_cols} FROM p WHERE address_key IS NOT NULL
    """)
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE lc_maj_all AS
        SELECT id, address_key AS k, issue_date AS d, address_key || '@' || issue_date::VARCHAR AS sk,
          reported_cost AS cost, pin10 FROM p
        WHERE permit_type IN ('PERMIT - NEW CONSTRUCTION', 'PERMIT - RENOVATION/ALTERATION')
          AND reported_cost >= {BIG_COST} AND address_key IS NOT NULL
    """)
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE lc_sig AS
        SELECT sk, k, d, cost, bucket, pid, cls FROM (
          SELECT sk, k, d, cost, pid, pc.cls AS cls, {class_bucket_sql("pc.cls")} AS bucket,
            lag(d) OVER (PARTITION BY k ORDER BY d) AS prev
          FROM (SELECT sk, k, d, max(cost) AS cost, first(pin10 ORDER BY cost DESC, id) AS pin10,
                  first(id ORDER BY cost DESC, id) AS pid
                FROM lc_maj_all GROUP BY sk, k, d) m
          LEFT JOIN lc_pin_class pc USING (pin10)
        ) WHERE (prev IS NULL OR d - prev > {FOLLOW_WINDOW}) AND d >= DATE '{R4_START}'
    """)
    con.execute("""
        CREATE OR REPLACE TEMP TABLE lc_mpp AS
        SELECT DISTINCT m.sk, c.name_key FROM lc_maj_all m JOIN lc_ctr c ON c.permit_id = m.id
    """)
    flags = ", ".join(f"t.f_{n}" for n in FOLLOW_TRADES)
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE lc_pr AS
        SELECT s.sk, s.d AS sd, s.bucket, t.id AS tid, t.d - s.d AS days, {flags},
          EXISTS (SELECT 1 FROM lc_ctr c WHERE c.permit_id = t.id) AS named
        FROM lc_sig s JOIN lc_fo t ON t.k = s.k AND t.d > s.d AND t.d <= s.d + INTERVAL {FOLLOW_WINDOW} DAY
    """)
    con.execute("""
        CREATE OR REPLACE TEMP TABLE lc_lk AS
        SELECT DISTINCT pr.sk, pr.tid FROM lc_pr pr JOIN lc_ctr c ON c.permit_id = pr.tid
        JOIN lc_mpp m ON m.name_key = c.name_key AND m.sk = pr.sk
    """)
    con.execute("""
        CREATE OR REPLACE TEMP TABLE lc_pr2 AS
        SELECT pr.*, (lk.tid IS NOT NULL) AS locked FROM lc_pr pr LEFT JOIN lc_lk lk USING (sk, tid)
    """)
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE lc_qd29 AS
        SELECT unnest(generate_series(DATE '{R4_START}', {end_sql}, INTERVAL 3 MONTH))::DATE AS q
    """)
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE lc_pool_a AS
        SELECT a.address_key AS k, lc_qd29.q, a.bucket FROM (SELECT DISTINCT address_key, bucket FROM lc_addr_cls
          WHERE bucket IN ({BUCKET_LIST_29})) a CROSS JOIN lc_qd29
        WHERE NOT EXISTS (SELECT 1 FROM lc_maj_all m WHERE m.k = a.address_key
          AND m.d > lc_qd29.q - INTERVAL {FOLLOW_WINDOW} DAY AND m.d <= lc_qd29.q + INTERVAL {FOLLOW_WINDOW} DAY)
    """)
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE lc_pool_b AS
        SELECT DISTINCT a.k, a.q, a.bucket FROM (
          SELECT p2.address_key AS k, lc_qd29.q, ac.bucket FROM p p2 CROSS JOIN lc_qd29
          JOIN (SELECT DISTINCT address_key, bucket FROM lc_addr_cls WHERE bucket IN ({BUCKET_LIST_29})) ac
            ON ac.address_key = p2.address_key
          WHERE p2.permit_type IN ('PERMIT - NEW CONSTRUCTION', 'PERMIT - RENOVATION/ALTERATION')
            AND p2.reported_cost >= 100000 AND p2.reported_cost < {BIG_COST}
            AND p2.issue_date > lc_qd29.q - INTERVAL 90 DAY AND p2.issue_date <= lc_qd29.q
        ) a
        WHERE NOT EXISTS (SELECT 1 FROM lc_maj_all m WHERE m.k = a.k
          AND m.d > a.q - INTERVAL {FOLLOW_WINDOW} DAY AND m.d <= a.q + INTERVAL {FOLLOW_WINDOW} DAY)
    """)
    for pool in ("a", "b"):
        con.execute(f"""
            CREATE OR REPLACE TEMP TABLE lc_hit_{pool} AS
            SELECT c.k, c.q, {", ".join(f"bool_or(t.f_{n}) AS f_{n}" for n in FOLLOW_TRADES)}
            FROM lc_pool_{pool} c JOIN lc_fo t ON t.k = c.k AND t.d > c.q AND t.d <= c.q + INTERVAL {FOLLOW_WINDOW} DAY
            GROUP BY c.k, c.q
        """)

    def cohort_end(trade: str | None) -> str:
        if trade == "scaffolding":
            return f"least({end_sql}, DATE '{SCAFFOLD_LAST}' - INTERVAL {FOLLOW_WINDOW} DAY)"
        return end_sql

    def pool_rate(pool: str, flag_expr: str, weights: dict[str, float], e: str) -> float:
        rows = q(
            con,
            f"""
            SELECT c.bucket, count(*) AS n, count(*) FILTER (WHERE {flag_expr}) AS hits
            FROM lc_pool_{pool} c LEFT JOIN lc_hit_{pool} h ON h.k = c.k AND h.q = c.q
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
            WITH s AS (SELECT * FROM lc_sig WHERE d <= {e} AND bucket IN ({BUCKET_LIST_29})),
            per AS (
              SELECT s.sk, s.bucket, min(r.days) FILTER (WHERE {sflag}) AS first_days,
                bool_or(({sflag}) AND r.named AND NOT r.locked) AS has_new,
                bool_or(({sflag}) AND r.named AND r.locked) AS has_locked,
                bool_or(({sflag}) AND NOT r.named) AS has_unnamed,
                EXISTS (SELECT 1 FROM lc_fo x WHERE x.k = s.k AND ({" OR ".join(f"x.f_{n}" for n in any_of)})
                  AND x.d > s.d - INTERVAL {2 * FOLLOW_WINDOW} DAY AND x.d <= s.d - INTERVAL {FOLLOW_WINDOW} DAY)
                  AS before
              FROM s LEFT JOIN lc_pr2 r ON r.sk = s.sk GROUP BY s.sk, s.k, s.d, s.bucket
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
        base_a = pool_rate("a", hflag, weights, e)
        base_b = pool_rate("b", hflag, weights, e)
        t = one(
            con,
            f"""
            SELECT count(*) AS n, count(*) FILTER (WHERE named) AS named_n,
              count(*) FILTER (WHERE named AND locked) AS locked_n,
              count(*) FILTER (WHERE named AND NOT locked) AS new_n
            FROM lc_pr2 r WHERE r.sd <= {e} AND r.bucket IN ({BUCKET_LIST_29}) AND ({sflag})
        """,
        )
        tm = one(
            con,
            f"""
            WITH s AS (SELECT * FROM lc_sig WHERE d <= {e} AND bucket IN ({BUCKET_LIST_29})),
            per AS (SELECT s.sk, min(r.days) AS first_days FROM s JOIN lc_pr2 r ON r.sk = s.sk AND ({sflag}) GROUP BY s.sk)
            SELECT {_quartiles("first_days")} FROM per
        """,
        )
        before = sum(r["before_hits"] for r in sig_rows)
        return {
            "signals": n,
            "followon_rate": hits / n,
            "own_earlier_rate": before / n,
            "lift_vs_own": hits / n / (before / n) if before else None,
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
        }

    by_trade = []
    for name in FOLLOW_TRADES:
        st = trade_stats(name, (name,))
        by_trade.append(
            {"trade": name, "permit_types": FOLLOW_TRADES[name][1]}
            | {k: v for k, v in st.items() if not k.startswith("_")}
        )
    head = trade_stats("headline", HEADLINE_TRADES)
    by_class = []
    for r in head["_by_bucket"]:
        base_a = pool_rate("a", " OR ".join(f"h.f_{n}" for n in HEADLINE_TRADES), {r["bucket"]: 1.0}, end_sql)
        by_class.append(
            {
                "class": r["bucket"],
                "signals": r["n"],
                "followon_rate": r["hits"] / r["n"],
                "matched_control_rate": base_a,
                "lift_vs_matched": r["hits"] / r["n"] / base_a if base_a else None,
            }
        )
    headline_flag = " OR ".join(f"r.f_{n}" for n in HEADLINE_TRADES)
    unknown = one(
        con,
        f"""
        SELECT count(*) AS n, avg((EXISTS (SELECT 1 FROM lc_pr2 r WHERE r.sk = s.sk AND ({headline_flag})))::INT) AS rate
        FROM lc_sig s WHERE s.d <= {end_sql} AND s.bucket NOT IN ({BUCKET_LIST_29})
    """,
    )
    by_year = q(
        con,
        f"""
        SELECT year(s.d) AS year, count(*) AS n,
          avg((EXISTS (SELECT 1 FROM lc_pr2 r WHERE r.sk = s.sk AND ({headline_flag})))::INT) AS conversion
        FROM lc_sig s WHERE s.d <= {end_sql} AND s.bucket IN ({BUCKET_LIST_29}) GROUP BY 1 ORDER BY 1
    """,
    )
    vol = one(
        con,
        f"""
        SELECT count(*) FILTER (WHERE bucket NOT IN ('{BUCKET_RESIDENTIAL}', '{BUCKET_VACANT}')) / 52.0 AS v,
          count(*) FILTER (WHERE bucket IN ({BUCKET_LIST_29})) / 52.0 AS v_known
        FROM lc_sig WHERE d > DATE '{max_issue}' - INTERVAL 365 DAY
    """,
    )
    return {
        "signals": head["signals"],
        "conversion": head["followon_rate"],
        "baseline": head["own_earlier_rate"],
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
        "period_end": one(con, f"SELECT ({end_sql})::DATE AS d")["d"],
    }


def recent_big_permits(con, *, asof: str, days: int = 365) -> list[dict]:
    """Big-permit episodes (lc_sig, so `open_trades` must have run) in the `days` days up to `asof`, excluding
    single-family and vacant-land classes (the lab's volume definition), newest first with explicit tie-breaks.
    Each row carries `appeared`: follow-on trades already seen at the address since the permit (scaffolding is
    left out: the feed stopped carrying it)."""
    trades = [n for n in FOLLOW_TRADES if n != "scaffolding"]
    seen = ", ".join(f"coalesce(bool_or(t.f_{n}), false) AS a_{n}" for n in trades)
    rows = q(
        con,
        f"""
        SELECT s.sk, s.k, s.d, s.cost, s.bucket, s.pid, s.cls, {seen}
        FROM lc_sig s LEFT JOIN lc_fo t ON t.k = s.k AND t.d > s.d AND t.d <= DATE '{asof}'
        WHERE s.d > DATE '{asof}' - INTERVAL {days} DAY AND s.d <= DATE '{asof}'
          AND s.bucket NOT IN ('{BUCKET_RESIDENTIAL}', '{BUCKET_VACANT}')
        GROUP BY s.sk, s.k, s.d, s.cost, s.bucket, s.pid, s.cls
        ORDER BY s.d DESC, s.cost DESC, s.pid
    """,
    )
    for r in rows:
        r["appeared"] = [n for n in trades if r.pop(f"a_{n}")]
    return rows
