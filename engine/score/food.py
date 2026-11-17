"""Restaurant-inspection signals matched against ordinary inspections (signal lab H23-H26 method).

Used by the lead snapshot (closed-restaurant leads) and the backtests (BT8), so the formula that was validated
historically is exactly the formula that scores live leads. The signal lab imports the shared definitions below
(VALID_RESULT, INSPECTION_STRATA, NAME_KEY, SAME_NAME, RENO_PREDICATE, round_floats); its `inspection_vs_control`
is a generalization (any key, an observed-window variant for H23) of the address-keyed function here; on H26 the
two give the same numbers (BT8 and the lab's H26 share the period 2016-01-01 to 2025-11-01).

Requires the warehouse tables `food_inspections` and whatever the target SQL reads (`food_licenses`, `p` from
`prepare_base`). All temp tables are prefixed `fd_` so they never collide with the snapshot's own.
"""

from __future__ import annotations

from engine.score.signals import one, q

VALID_RESULT = "results IN ('Pass', 'Pass w/ Conditions', 'Fail')"
INSPECTION_STRATA = """CASE
  WHEN inspection_type = 'License' THEN 'License (pre-opening)'
  WHEN lower(inspection_type) LIKE '%re-inspection%' THEN 'Re-inspection'
  WHEN inspection_type LIKE '%Complaint%' THEN 'Complaint'
  WHEN inspection_type = 'Canvass' THEN 'Canvass (routine)'
  ELSE 'Other' END"""
NAME_KEY = "regexp_replace(upper(coalesce({x}, '')), '[^A-Z0-9]', '', 'g')"
SAME_NAME = "(e.nm = t.nm OR (length(e.nm) >= 6 AND length(t.nm) >= 6 AND (contains(e.nm, t.nm) OR contains(t.nm, e.nm))))"

CLOSED = "results = 'Out of Business'"
NEW_LICENSE_SQL = (
    f"SELECT address_key AS k, issue_date AS d, {NAME_KEY.format(x='dba')} AS nm FROM food_licenses "
    "WHERE address_key IS NOT NULL AND issue_date IS NOT NULL"
)
RENO_PREDICATE = (
    "(permit_type = 'PERMIT - RENOVATION/ALTERATION' OR t_interior_buildout OR t_new_construction)"
)
RENO_SQL = f"SELECT address_key AS k, issue_date AS d, '' AS nm FROM p WHERE address_key IS NOT NULL AND {RENO_PREDICATE}"


def round_floats(x, digits: int = 4):
    """Round every float in nested results so written files are byte-stable across runs."""
    if isinstance(x, float):
        return round(x, digits)
    if isinstance(x, dict):
        return {k: round_floats(v, digits) for k, v in x.items()}
    if isinstance(x, list):
        return [round_floats(v, digits) for v in x]
    return x


def inspection_vs_control(
    con,
    *,
    sig_where: str,
    ctl_where: str,
    target_sql: str,
    start: str,
    end: str,
    window: int = 365,
    cond: str = "true",
    min_days: int = 0,
) -> dict:
    """Restaurant inspections showing a condition (signal) vs ordinary restaurant inspections without it.

    Keyed by street address (restaurants only). Both groups are one inspection per address per `window` days, and
    both must have no signal-type inspection at the address in the previous `window` days. Control conversion is
    standardized to the signal group's inspection-type mix (a pre-opening 'License' inspection is a very different
    starting point from a routine canvass). target_sql -> (k, d, nm). cond may use e.nm / t.nm. min_days drops
    targets that follow too quickly. Floats are returned unrounded.
    """
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE fd_fi AS
        SELECT address_key AS k, inspection_date AS d, inspection_id, {INSPECTION_STRATA} AS strat, results,
          {NAME_KEY.format(x="dba")} AS nm, ({sig_where}) AS is_sig, ({ctl_where}) AS is_ctl
        FROM food_inspections WHERE facility_type = 'Restaurant' AND address_key IS NOT NULL
    """)
    con.execute(f"CREATE OR REPLACE TEMP TABLE fd_tgt AS {target_sql}")
    con.execute("""
        CREATE OR REPLACE TEMP TABLE fd_sig_all AS
        SELECT k, d, min(strat) AS strat, min(nm) AS nm, min(results) AS results FROM fd_fi WHERE is_sig GROUP BY k, d
    """)
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE fd_sig_first AS
        SELECT k, d, strat, nm, results FROM (
          SELECT *, lag(d) OVER (PARTITION BY k ORDER BY d) AS prev FROM fd_sig_all
        ) WHERE prev IS NULL OR d - prev > {window}
    """)
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE fd_sig_ep AS
        SELECT * FROM fd_sig_first WHERE d BETWEEN DATE '{start}' AND DATE '{end}'
    """)
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE fd_ctl_ep AS
        SELECT k, d, strat, nm, results FROM (
          SELECT *, lag(d) OVER (PARTITION BY k ORDER BY d) AS prev FROM (
            SELECT c.k, c.d, min(c.strat) AS strat, min(c.nm) AS nm, min(c.results) AS results
            FROM fd_fi c WHERE c.is_ctl AND NOT EXISTS (
              SELECT 1 FROM fd_sig_all s WHERE s.k = c.k AND s.d > c.d - INTERVAL {window} DAY AND s.d <= c.d)
            GROUP BY c.k, c.d
          )
        ) WHERE (prev IS NULL OR d - prev > {window}) AND d BETWEEN DATE '{start}' AND DATE '{end}'
    """)
    for name in ("sig", "ctl"):
        con.execute(f"""
            CREATE OR REPLACE TEMP TABLE fd_res_{name} AS
            SELECT e.k, e.d, e.strat, e.results,
              min(t.d - e.d) FILTER (WHERE t.d > e.d + INTERVAL {min_days} DAY
                AND t.d <= e.d + INTERVAL {window} DAY AND ({cond})) AS days
            FROM fd_{name}_ep e LEFT JOIN fd_tgt t ON t.k = e.k
              AND t.d > e.d - INTERVAL {2 * window} DAY AND t.d <= e.d + INTERVAL {window} DAY
            GROUP BY e.k, e.d, e.strat, e.nm, e.results
        """)
    strata = q(
        con,
        """
        WITH s AS (SELECT strat, count(*) AS n, sum((days IS NOT NULL)::INT) AS hits FROM fd_res_sig GROUP BY 1),
        c AS (SELECT strat, count(*) AS n, sum((days IS NOT NULL)::INT) AS hits FROM fd_res_ctl GROUP BY 1)
        SELECT s.strat, s.n AS signals, s.hits AS signal_hits, c.n AS controls, c.hits AS control_hits
        FROM s LEFT JOIN c USING (strat) ORDER BY s.strat
    """,
    )
    signals = sum(r["signals"] for r in strata)
    usable = [r for r in strata if r["controls"]]
    weight = sum(r["signals"] for r in usable)
    baseline = sum(r["signals"] / weight * r["control_hits"] / r["controls"] for r in usable)
    hits = sum(r["signal_hits"] for r in strata)
    sg = one(
        con,
        """
        SELECT median(days) AS median_days, quantile_cont(days, 0.25) AS p25, quantile_cont(days, 0.75) AS p75,
          min(d) AS first_signal, max(d) AS last_signal
        FROM fd_res_sig
    """,
    )
    delays = [r["days"] for r in q(con, "SELECT days FROM fd_res_sig WHERE days IS NOT NULL ORDER BY days")]
    latest = "(SELECT max(inspection_date) FROM food_inspections)"
    volume = one(
        con,
        f"""
        SELECT (SELECT count(*) FROM fd_sig_all WHERE d > {latest} - INTERVAL 365 DAY) / 52.0 AS closures,
               (SELECT count(*) FROM fd_sig_first WHERE d > {latest} - INTERVAL 365 DAY) / 52.0 AS episodes
    """,
    )
    ctl_year = {
        r["year"]: r
        for r in q(
            con,
            "SELECT year(d) AS year, count(*) AS controls, avg((days IS NOT NULL)::INT) AS conversion "
            "FROM fd_res_ctl GROUP BY 1",
        )
    }
    by_year = q(
        con,
        "SELECT year(d) AS year, count(*) AS signals, avg((days IS NOT NULL)::INT) AS conversion "
        "FROM fd_res_sig GROUP BY 1 ORDER BY 1",
    )
    for r in by_year:
        c = ctl_year.get(r["year"])
        r["control_conversion"] = c["conversion"] if c else None
    return {
        "signals": signals,
        "conversion": hits / signals if signals else None,
        "baseline": baseline,
        "lift": hits / signals / baseline if signals and baseline else None,
        "median_days": sg["median_days"],
        "days_p25": sg["p25"],
        "days_p75": sg["p75"],
        "delays": delays,
        "first_signal": sg["first_signal"],
        "last_signal": sg["last_signal"],
        "closures_per_week": volume["closures"],
        "episodes_per_week": volume["episodes"],
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


CLOSURE_VIEWS = {
    "license": dict(target_sql=NEW_LICENSE_SQL, cond=f"NOT {SAME_NAME}"),
    "license_after30": dict(target_sql=NEW_LICENSE_SQL, cond=f"NOT {SAME_NAME}", min_days=30),
    "license_any": dict(target_sql=NEW_LICENSE_SQL),
    "permit": dict(target_sql=RENO_SQL),
}


def closure_views(con, *, start: str, end: str, only: tuple[str, ...] | None = None) -> dict:
    """The H26 views of 'Out of Business' restaurant closures, keyed by address.

    license = new retail food license under a different business name within 365 days (headline);
    license_after30 = the same but issued 31+ days after the closure was recorded (the actionable view);
    license_any = any new license including the same name; permit = renovation, build-out or new-construction
    permit at the address within 365 days. Requires the base temp table `p` (prepare_base).
    """
    return {
        name: inspection_vs_control(
            con, sig_where=CLOSED, ctl_where=VALID_RESULT, start=start, end=end, **spec
        )
        for name, spec in CLOSURE_VIEWS.items()
        if only is None or name in only
    }
