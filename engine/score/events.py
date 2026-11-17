"""Round 6 definitions: recurring event series, listing lead times, dumpster permits and pre-opening windows.

Used by the signal lab (H38-H41). Needs the warehouse tables `park_events`, `street_events` (CDOT festival, parade,
athletic, assembly, block-party and sidewalk-sale permits), `dumpster_permits` (CDOT), `food_inspections`,
`biz_license_history` and, for the dumpster and pre-opening parts, the lab's temp table `p` (issued building permits,
from `engine.score.signals.prepare_base`).

Privacy: Park District requestors and CDOT applicants who are individuals are never selected or reported; event keys
and organization names are used for matching only and never leave this module. Only counts and rates are returned.
"""

from __future__ import annotations

from engine.enrich.names import distinctive, normalize, token_set_ratio
from engine.score.signals import one, q

DATE_TOL = 31  # a recurrence counts when it lands within +/- this many days of the same date one year later
FIRST_YEAR, LAST_YEAR_CAP = 2014, 2025
# Prediction years left out of the pooled figures: the Park District held 72% fewer events in 2020 (so 2019 -> 2020
# recurrence is a pandemic result), and 2021 features rest on that gap. Every year is still shown in by_year.
COVID_YEARS = (2019, 2020, 2021)
MIN_RATE_N = 20  # fewest cases for a table cell to show a rate
GROUP_ORDER = (
    "Event 1",
    "Event 2",
    "Event 3",
    "Event 4",
    "Event 5",
    "Event 6 / Festival",
    "Corporate",
    "Promotions",
    "Venue (civic/corporate/philanthropic)",
)
CDOT_LARGE = ("Festival", "Parade", "Athletic", "Assembly")


def _rate(hits: int | None, n: int | None, min_n: int = MIN_RATE_N) -> float | None:
    return None if not n or n < min_n or hits is None else hits / n


# --- H38: recurring event series -------------------------------------------------------------------------------
def build_series(con, name: str, src_sql: str, as_of: str) -> None:
    """Temp tables `{name}_rows` (k, pk, d, grp, has_org), `{name}_sy` (one row per series-year) and `{name}_pred`
    (one row per series-year with the history features known at the end of that year and the next-year outcome).

    A series is an event key at a place (`pk`). `anchor` is the first date of the series in the year. A series
    'recurs' when any row lands within DATE_TOL days of anchor + 1 year; features use only earlier years.
    """
    con.execute(
        f"CREATE OR REPLACE TEMP TABLE {name}_rows AS "
        f"SELECT k, pk, d, grp, has_org FROM ({src_sql}) WHERE d <= DATE '{as_of}'"
    )
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE {name}_sy AS
        SELECT k, pk, year(d) AS y, first(grp ORDER BY d, grp) AS grp, min(d) AS anchor, max(d) AS last_d,
            count(*) AS n_rows, bool_or(has_org) AS has_org
        FROM {name}_rows GROUP BY k, pk, year(d)
    """)
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE {name}_win AS
        SELECT a.k, a.pk, a.y, min(r.d) AS first_hit
        FROM {name}_sy a JOIN {name}_rows r ON r.k = a.k AND r.pk = a.pk
         AND r.d BETWEEN a.anchor + INTERVAL 1 YEAR - INTERVAL {DATE_TOL} DAY
                     AND a.anchor + INTERVAL 1 YEAR + INTERVAL {DATE_TOL} DAY
        GROUP BY a.k, a.pk, a.y
    """)
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE {name}_pred AS
        SELECT a.k, a.pk, a.y, a.grp, a.anchor, a.has_org,
            (a.anchor + INTERVAL 1 YEAR)::DATE AS predicted,
            p1.y IS NOT NULL AS held2, (p1.y IS NOT NULL AND p2.y IS NOT NULL) AS held3,
            f.first_y = a.y AS debut,
            (a.anchor + INTERVAL 1 YEAR + INTERVAL {DATE_TOL} DAY)::DATE <= DATE '{as_of}' AS evaluable,
            w.first_hit IS NOT NULL AS hit, w.first_hit,
            nx.y IS NOT NULL AS hit_any_next_year,
            CASE WHEN nx.y IS NOT NULL THEN abs(dayofyear(nx.anchor) - dayofyear(a.anchor)) END AS shift_days
        FROM {name}_sy a
        LEFT JOIN {name}_sy p1 ON p1.k = a.k AND p1.pk = a.pk AND p1.y = a.y - 1
        LEFT JOIN {name}_sy p2 ON p2.k = a.k AND p2.pk = a.pk AND p2.y = a.y - 2
        LEFT JOIN {name}_sy nx ON nx.k = a.k AND nx.pk = a.pk AND nx.y = a.y + 1
        LEFT JOIN (SELECT k, pk, min(y) AS first_y FROM {name}_sy GROUP BY k, pk) f ON f.k = a.k AND f.pk = a.pk
        LEFT JOIN {name}_win w ON w.k = a.k AND w.pk = a.pk AND w.y = a.y
        WHERE a.y BETWEEN {FIRST_YEAR} AND {LAST_YEAR_CAP}
    """)


def series_metrics(con, name: str, as_of: str) -> dict:
    """Precision of 'held in each of the last 2 / 3 years' and of the debut-year base rate, by group and year, date
    stability and the lead time of the predictions (prediction date = 31 December of the year of the features)."""
    pred = f"{name}_pred"
    ok = f"y NOT IN {COVID_YEARS}"
    rules = q(
        con,
        f"""
        SELECT rule, count(*) AS series_years, count(*) FILTER (WHERE hit) AS hits FROM (
          SELECT 1 AS o, 'every series held in the year (no history needed)' AS rule, hit FROM {pred} WHERE evaluable AND {ok}
          UNION ALL SELECT 2, 'debut year (not seen in any earlier year)', hit FROM {pred} WHERE evaluable AND {ok} AND debut
          UNION ALL SELECT 3, 'held in each of the last 2 years', hit FROM {pred} WHERE evaluable AND {ok} AND held2
          UNION ALL SELECT 4, 'held in each of the last 3 years', hit FROM {pred} WHERE evaluable AND {ok} AND held3
          UNION ALL SELECT 5, 'held in each of the last 2 years, organization named', hit
            FROM {pred} WHERE evaluable AND {ok} AND held2 AND has_org
        ) GROUP BY o, rule ORDER BY o
    """,
    )
    for r in rules:
        r["precision_rate"] = _rate(r["hits"], r["series_years"], 1)
    by_group = q(
        con,
        f"""
        SELECT grp AS "group",
          count(*) FILTER (WHERE debut) AS debut_n, count(*) FILTER (WHERE debut AND hit) AS debut_hits,
          count(*) FILTER (WHERE held2) AS held2_n, count(*) FILTER (WHERE held2 AND hit) AS held2_hits,
          count(*) FILTER (WHERE held3) AS held3_n, count(*) FILTER (WHERE held3 AND hit) AS held3_hits
        FROM {pred} WHERE evaluable AND {ok} GROUP BY grp
    """,
    )
    order = {g: i for i, g in enumerate(GROUP_ORDER)}
    by_group.sort(key=lambda r: (order.get(r["group"], 99), r["group"]))
    for r in by_group:
        r["debut_rate"] = _rate(r["debut_hits"], r["debut_n"])
        r["held2_rate"] = _rate(r["held2_hits"], r["held2_n"])
        r["held3_rate"] = _rate(r["held3_hits"], r["held3_n"])
    # Headline: held-2-years precision against the debut base rate, both over the groups that have enough debut
    # cases, with the base rate weighted to the held-2 group mix so group composition does not drive the lift.
    use = [r for r in by_group if r["debut_n"] >= MIN_RATE_N and r["held2_n"] > 0]
    n2 = sum(r["held2_n"] for r in use)
    hits2 = sum(r["held2_hits"] for r in use)
    base = sum(r["held2_n"] * r["debut_hits"] / r["debut_n"] for r in use) / n2 if n2 else None
    conv = hits2 / n2 if n2 else None
    by_year = q(
        con,
        f"""
        SELECT y AS year,
          count(*) FILTER (WHERE held2) AS recurring_series, count(*) FILTER (WHERE held3) AS recurring_3_years,
          count(*) FILTER (WHERE held2 AND evaluable) AS evaluated,
          count(*) FILTER (WHERE held2 AND evaluable AND hit) AS hits,
          count(*) FILTER (WHERE debut AND evaluable) AS debut_n,
          count(*) FILTER (WHERE debut AND evaluable AND hit) AS debut_hits
        FROM {pred} GROUP BY y ORDER BY y
    """,
    )
    for r in by_year:
        r["held2_rate"] = _rate(r["hits"], r["evaluated"], 10)
        r["debut_rate"] = _rate(r["debut_hits"], r["debut_n"], 10)
    by_period = q(
        con,
        f"""
        SELECT CASE WHEN y <= 2018 THEN '2014-2018 (before the pandemic)' ELSE '2022-2025 (after)' END AS period,
          count(*) FILTER (WHERE held2 AND evaluable) AS held2_n,
          count(*) FILTER (WHERE held2 AND evaluable AND hit) AS held2_hits,
          count(*) FILTER (WHERE held3 AND evaluable) AS held3_n,
          count(*) FILTER (WHERE held3 AND evaluable AND hit) AS held3_hits,
          count(*) FILTER (WHERE debut AND evaluable) AS debut_n,
          count(*) FILTER (WHERE debut AND evaluable AND hit) AS debut_hits,
          count(*) FILTER (WHERE evaluable) AS all_series_n, count(*) FILTER (WHERE evaluable AND hit) AS all_series_hits
        FROM {pred} WHERE {ok} GROUP BY 1 ORDER BY 1
    """,
    )
    for r in by_period:
        r["held2_rate"] = _rate(r["held2_hits"], r["held2_n"])
        r["held3_rate"] = _rate(r["held3_hits"], r["held3_n"])
        r["debut_rate"] = _rate(r["debut_hits"], r["debut_n"])
        r["all_series_rate"] = _rate(r["all_series_hits"], r["all_series_n"])
    last_y = int(as_of[:4]) - 1
    org = one(
        con,
        f"""
        SELECT count(*) AS series_years, avg(has_org::INT) AS organization_named_share,
          count(*) FILTER (WHERE held2) AS recurring_series_years,
          avg(has_org::INT) FILTER (WHERE held2) AS recurring_organization_named_share
        FROM {pred} WHERE y > {last_y - 3}
    """,
    )
    shift = one(
        con,
        f"""
        SELECT count(*) AS n, median(shift_days) AS median_shift_days, quantile_cont(shift_days, 0.75) AS p75_shift_days,
          avg((shift_days <= 7)::INT) AS within_7_days_share, avg((shift_days <= {DATE_TOL})::INT) AS within_31_days_share
        FROM {pred} WHERE held2 AND hit_any_next_year AND y < {last_y} AND {ok}
    """,
    )
    lead = one(
        con,
        f"""
        SELECT count(*) AS n, median(first_hit - make_date(y, 12, 31)) AS median_lead_days,
          quantile_cont(first_hit - make_date(y, 12, 31), 0.25) AS p25_lead_days,
          quantile_cont(first_hit - make_date(y, 12, 31), 0.75) AS p75_lead_days
        FROM {pred} WHERE held2 AND evaluable AND hit AND {ok}
    """,
    )
    pipeline = q(
        con,
        f"""
        SELECT grp AS "group",
          count(*) FILTER (WHERE held2 AND predicted - make_date(y, 12, 31) BETWEEN 90 AND 270
                           AND y > {last_y - 3}) / 3.0 AS predicted_3_to_9_months_per_year,
          count(*) FILTER (WHERE held2 AND predicted - make_date(y, 12, 31) BETWEEN 90 AND 270
                           AND y > {last_y - 3} AND evaluable AND hit) AS hits_in_window,
          count(*) FILTER (WHERE held2 AND predicted - make_date(y, 12, 31) BETWEEN 90 AND 270
                           AND y > {last_y - 3} AND evaluable) AS evaluated_in_window
        FROM {pred} GROUP BY grp
    """,
    )
    pipeline.sort(key=lambda r: (order.get(r["group"], 99), r["group"]))
    for r in pipeline:
        r["hit_rate"] = _rate(r["hits_in_window"], r["evaluated_in_window"], 10)
    recent = [r for r in by_year if r["year"] > last_y - 3]
    return {
        "series_years_held2": n2,
        "conversion": conv,
        "baseline": base,
        "lift": conv / base if conv is not None and base else None,
        "recurring_per_year_last3": sum(r["recurring_series"] for r in recent) / 3.0,
        "by_rule": rules,
        "by_group": by_group,
        "by_period": by_period,
        "by_year": by_year,
        "date_stability": shift,
        "lead_time": lead,
        "pipeline": pipeline,
        "organization_named": org,
    }


def park_series_src() -> str:
    return """
        SELECT event_key AS k, coalesce(park_no::VARCHAR, 'n:' || park_name) AS pk, start_date AS d, grp,
            organization IS NOT NULL AS has_org
        FROM park_events WHERE is_real AND is_held AND event_key IS NOT NULL
    """


def cdot_series_src() -> str:
    """Large formal street events (festival, parade, athletic, assembly) that took place, keyed by name and ward."""
    types = ", ".join(f"'{t}'" for t in CDOT_LARGE)
    return f"""
        SELECT event_key AS k, coalesce(ward::VARCHAR, '?') AS pk, start_date AS d, worktype AS grp,
            applicant_org IS NOT NULL AS has_org
        FROM street_events WHERE worktype IN ({types}) AND milestone = 'Complete' AND event_key IS NOT NULL
    """


# --- organization matching (names only; never reported) -------------------------------------------------------
FUZZY_MIN = 0.9
MAX_BLOCK = 400  # a token shared by more names than this does not block a fuzzy comparison


def _name_index(names: set[str]) -> tuple[set[str], dict[str, list[str]]]:
    blocks: dict[str, list[str]] = {}
    for key in sorted(names):
        for tok in set(distinctive(key)):
            blocks.setdefault(tok, []).append(key)
    return names, blocks


def _match(key: str, index: tuple[set[str], dict[str, list[str]]]) -> str | None:
    names, blocks = index
    if key in names:
        return "exact"
    for tok in sorted(set(distinctive(key))):
        cands = blocks.get(tok, [])
        if len(cands) <= MAX_BLOCK and any(token_set_ratio(key, c) >= FUZZY_MIN for c in cands):
            return "fuzzy"
    return None


def org_match(con, orgs_sql: str) -> dict:
    """Share of distinct organizations (by normalized name) found among Overture places in Chicago and among Chicago
    business license names (legal name or DBA, history plus current). exact = same normalized name; fuzzy adds a
    token-set similarity of at least 0.9 on a shared distinctive word. A name match is not a contact."""
    keys = sorted({normalize(r[0]) for r in con.execute(orgs_sql).fetchall()} - {""})
    places = {
        normalize(r[0])
        for r in con.execute(
            "SELECT DISTINCT name FROM places WHERE in_chicago AND name IS NOT NULL"
        ).fetchall()
    } - {""}
    lic = {
        normalize(r[0])
        for r in con.execute(
            "SELECT legal_name FROM biz_license_history UNION SELECT dba FROM biz_license_history "
            "UNION SELECT legal_name FROM biz_licenses UNION SELECT dba FROM biz_licenses"
        ).fetchall()
        if r[0]
    } - {""}
    pi, li = _name_index(places), _name_index(lic)
    n = len(keys)
    out = {
        "organizations": n,
        "place_exact": 0,
        "place_any": 0,
        "license_exact": 0,
        "license_any": 0,
        "any_match": 0,
    }
    for key in keys:
        mp, ml = _match(key, pi), _match(key, li)
        out["place_exact"] += mp == "exact"
        out["place_any"] += mp is not None
        out["license_exact"] += ml == "exact"
        out["license_any"] += ml is not None
        out["any_match"] += mp is not None or ml is not None
    for k in ("place_exact", "place_any", "license_exact", "license_any", "any_match"):
        out[f"{k}_share"] = out[k] / n if n else None
    return out


# --- H39: how far ahead do event permits become visible ----------------------------------------------------------
LEAD_THRESHOLDS = (14, 30, 60, 90, 120, 180)


def park_listing(con) -> dict:
    """Park District feed: `listed_date` is Socrata's row-creation date (a bulk reload on `baseline`, then weekly
    batches). For events starting at least T days after the baseline, the share listed at least T days ahead is
    exact (no left-censoring); rows listed on the baseline have an unknown true lead of at least start - baseline."""
    b = one(
        con,
        "SELECT min(listed_date) AS baseline, max(listed_date) AS last_listed, max(start_date) AS feed_ends, "
        "count(*) FILTER (WHERE listed_date = (SELECT min(listed_date) FROM park_events)) AS baseline_rows, "
        "count(DISTINCT listed_date) AS load_dates FROM park_events",
    )
    baseline, last_listed = b["baseline"], b["last_listed"]
    real = "is_real AND is_held AND listed_date IS NOT NULL"
    rows = []
    for t in LEAD_THRESHOLDS:
        r = one(
            con,
            f"""
            SELECT count(*) AS events_in_scope,
              count(*) FILTER (WHERE start_date - listed_date >= {t}) AS listed_that_early
            FROM park_events WHERE {real} AND start_date >= DATE '{baseline}' + {t} AND start_date <= DATE '{last_listed}' + 400
        """,
        )
        rows.append(
            {
                "days_ahead": t,
                "rows_in_scope": r["events_in_scope"],
                "rows_listed_that_early": r["listed_that_early"],
                "listed_early_share": _rate(r["listed_that_early"], r["events_in_scope"], 1),
            }
        )
    grp = q(
        con,
        f"""
        SELECT grp AS "group", count(*) AS rows_in_scope,
          count(*) FILTER (WHERE start_date - listed_date >= 90) AS rows_listed_90_days_ahead
        FROM park_events WHERE {real} AND start_date >= DATE '{baseline}' + 90 GROUP BY grp
    """,
    )
    order = {g: i for i, g in enumerate(GROUP_ORDER)}
    grp.sort(key=lambda r: (order.get(r["group"], 99), r["group"]))
    for r in grp:
        r["listed_90_days_ahead_share"] = _rate(r["rows_listed_90_days_ahead"], r["rows_in_scope"], 1)
    new_rows = one(
        con,
        f"""
        SELECT count(*) AS rows, count(DISTINCT event_key || '|' || coalesce(park_no::VARCHAR, park_name)) AS series,
          median(start_date - listed_date) AS median_lead_days,
          quantile_cont(start_date - listed_date, 0.25) AS p25_lead_days,
          quantile_cont(start_date - listed_date, 0.75) AS p75_lead_days,
          avg((start_date >= listed_date)::INT) AS listed_before_event_share,
          avg((start_date - listed_date >= 30)::INT) AS ahead_30_days_share
        FROM park_events WHERE {real} AND listed_date > DATE '{baseline}'
    """,
    )
    new_rows["weeks_observed"] = (last_listed - baseline).days / 7
    future = one(
        con,
        f"""
        SELECT count(*) FILTER (WHERE is_real AND is_held) AS real_rows_listed_after_today,
          count(DISTINCT CASE WHEN is_real AND is_held THEN event_key || '|' || coalesce(park_no::VARCHAR, park_name) END)
            AS real_series_after_today,
          count(*) AS all_rows_after_today
        FROM park_events WHERE start_date > DATE '{last_listed}'
    """,
    )
    all_new = one(
        con,
        f"""
        SELECT count(*) AS rows, median(start_date - listed_date) AS median_lead_days,
          avg((start_date - listed_date >= 90)::INT) AS share_90_days
        FROM park_events WHERE listed_date > DATE '{baseline}' AND start_date >= listed_date
    """,
    )
    return {
        "baseline": str(baseline),
        "last_listed": str(last_listed),
        "feed_ends": str(b["feed_ends"]),
        "baseline_rows": b["baseline_rows"],
        "load_dates": b["load_dates"],
        "total_rows": one(con, "SELECT count(*) AS n FROM park_events")["n"],
        "by_threshold": rows,
        "by_group": grp,
        "new_real_rows_since_baseline": new_rows,
        "all_new_rows_since_baseline": all_new,
        "listed_after_today": future,
    }


def event_license_lead(con) -> list[dict]:
    """Chicago business licenses tied to a single event (non-premises): days from application to license start."""
    rows = q(
        con,
        """
        SELECT license_description AS license_type, count(*) AS licenses, median(start_date - application_date) AS median_days,
          quantile_cont(start_date - application_date, 0.25) AS p25_days,
          quantile_cont(start_date - application_date, 0.75) AS p75_days,
          avg((start_date - application_date >= 30)::INT) AS ahead_30_days_share,
          avg((start_date - application_date >= 90)::INT) AS ahead_90_days_share
        FROM biz_license_history
        WHERE application_type = 'ISSUE' AND application_date IS NOT NULL AND start_date >= application_date
          AND license_description IN ('Special Event Liquor', 'Special Event Food', 'Indoor Special Event')
          AND issue_date >= DATE '2016-01-01'
        GROUP BY license_description ORDER BY licenses DESC, license_description
    """,
    )
    return rows


def cdot_lead(con) -> dict:
    """CDOT street-event permits (distinct permits that were not cancelled or denied and whose date has passed):
    lead = event start date minus the date CDOT began review (`processed_date`, the first date the data gives)."""
    as_of = one(con, "SELECT max(processed_date) AS d FROM street_events")["d"]
    con.execute("""
        CREATE OR REPLACE TEMP TABLE ce AS
        SELECT permit_no, worktype, min(start_date) AS d, min(processed_date) AS proc,
            bool_or(applicant_org IS NOT NULL) AS org, bool_or(applicant_is_person) AS person
        FROM street_events
        WHERE milestone NOT IN ('Cancelled', 'Denied') AND start_date >= DATE '2016-01-01'
          AND processed_date IS NOT NULL
        GROUP BY permit_no, worktype
    """)
    past = f"d <= DATE '{as_of}'"
    by_type = q(
        con,
        f"""
        SELECT worktype, count(*) AS permits, median(d - proc) AS median_lead_days,
          quantile_cont(d - proc, 0.25) AS p25_days, quantile_cont(d - proc, 0.75) AS p75_days,
          quantile_cont(d - proc, 0.9) AS p90_days,
          avg((d - proc >= 90)::INT) AS ahead_90_days_share, avg((d - proc >= 180)::INT) AS ahead_180_days_share,
          avg((d - proc >= 270)::INT) AS ahead_270_days_share, avg(org::INT) AS organization_applicant_share
        FROM ce WHERE {past} GROUP BY worktype ORDER BY permits DESC, worktype
    """,
    )
    large = ", ".join(f"'{t}'" for t in CDOT_LARGE)
    by_year = q(
        con,
        f"""
        SELECT year(d) AS year, count(*) AS permits, median(d - proc) AS median_lead_days,
          avg((d - proc >= 90)::INT) AS ahead_90_days_share,
          count(*) FILTER (WHERE d - proc >= 90) AS permits_90_days_ahead,
          avg(org::INT) AS organization_applicant_share
        FROM ce WHERE {past} AND worktype IN ({large}) GROUP BY 1 ORDER BY 1
    """,
    )
    weekly = one(
        con,
        f"""
        SELECT count(*) / 52.0 AS applications_per_week,
          count(*) FILTER (WHERE d - proc BETWEEN 90 AND 270) / 52.0 AS applications_3_to_9_months_ahead_per_week,
          count(*) FILTER (WHERE d - proc BETWEEN 90 AND 270 AND org) / 52.0 AS org_applicants_3_to_9_months_per_week
        FROM ce WHERE worktype IN ({large}) AND proc > DATE '{as_of}' - 364 AND proc <= DATE '{as_of}'
          AND d >= proc
    """,
    )
    # Applications still in 'Application Checks' or 'Incomplete Application' have no review date yet but are already
    # in the feed with their event date, so the pipeline counts every permit that is neither cancelled nor denied.
    pipeline = q(
        con,
        f"""
        SELECT worktype,
          count(*) FILTER (WHERE d - DATE '{as_of}' BETWEEN 1 AND 30) AS next_30_days,
          count(*) FILTER (WHERE d - DATE '{as_of}' BETWEEN 31 AND 90) AS days_31_to_90,
          count(*) FILTER (WHERE d - DATE '{as_of}' BETWEEN 91 AND 180) AS days_91_to_180,
          count(*) FILTER (WHERE d - DATE '{as_of}' BETWEEN 181 AND 365) AS days_181_to_365,
          count(*) FILTER (WHERE d - DATE '{as_of}' BETWEEN 91 AND 365 AND org) AS org_applicant_91_to_365
        FROM (
          SELECT permit_no, worktype, min(start_date) AS d, bool_or(applicant_org IS NOT NULL) AS org
          FROM street_events WHERE milestone NOT IN ('Cancelled', 'Denied') GROUP BY permit_no, worktype
        ) WHERE worktype IN ({large}) AND d > DATE '{as_of}' AND d <= DATE '{as_of}' + 365
        GROUP BY worktype ORDER BY worktype
    """,
    )
    return {
        "as_of": str(as_of),
        "by_type": by_type,
        "large_events_by_year": by_year,
        "weekly": weekly,
        "pipeline_today": pipeline,
    }


# --- H40: dumpster permits ---------------------------------------------------------------------------------------
DUMP_WINDOW = 180
DUMP_START = (
    "2017-01-01"  # dumpster permits start 2016-01-01, so the earlier-window baseline is complete from here
)
TYPE_SQL = (
    "CASE permit_type WHEN 'PERMIT - WRECKING/DEMOLITION' THEN 'demolition' "
    "WHEN 'PERMIT - NEW CONSTRUCTION' THEN 'new construction' ELSE 'renovation/alteration' END"
)
PROJECT_TYPES = (
    "('PERMIT - WRECKING/DEMOLITION', 'PERMIT - NEW CONSTRUCTION', 'PERMIT - RENOVATION/ALTERATION')"
)
HAULER_KEY = (
    "trim(regexp_replace(regexp_replace(regexp_replace(hauler, '[^A-Z0-9 ]', ' ', 'g'), "
    "'\\b(INC|INCORPORATED|LLC|L L C|CO|CORP|CORPORATION|COMPANY|LTD|LP|L P|THE)\\b', ' ', 'g'), ' +', ' ', 'g'))"
)


def _cost_band(cost: str) -> str:
    return (
        f"CASE WHEN {cost} >= 250000 THEN '$250k+' WHEN {cost} >= 50000 THEN '$50k-$250k' "
        f"WHEN {cost} >= 10000 THEN '$10k-$50k' WHEN {cost} > 0 THEN 'under $10k' ELSE 'no cost reported' END"
    )


def _std_control(ctl: dict[int, tuple[int, int]], sig_years: dict[int, int]) -> float | None:
    """Control hit rate standardized to the signals' year mix. ctl: year -> (n, hits); sig_years: year -> signals."""
    num = den = 0.0
    for y, n_sig in sig_years.items():
        n, hits = ctl.get(y, (0, 0))
        if n >= 100:
            num += n_sig * hits / n
            den += n_sig
    return num / den if den else None


def ensure_project_permits(con) -> None:
    """Temp table bd: one row per address and day with a renovation/alteration, new-construction or demolition permit
    (the costliest permit's type, cost and id). Needs the lab's temp table `p`."""
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE bd AS
        SELECT address_key AS k, issue_date AS d,
            first({TYPE_SQL} ORDER BY coalesce(reported_cost, 0) DESC, id) AS ptype,
            max(coalesce(reported_cost, 0)) AS cost, first(id ORDER BY coalesce(reported_cost, 0) DESC, id) AS pid
        FROM p WHERE address_key IS NOT NULL AND permit_type IN {PROJECT_TYPES} GROUP BY address_key, issue_date
    """)


def dumpster_prep(con, as_of: str, start: str = DUMP_START) -> str:
    """Temp tables dmp (one issued dumpster permit per permit and address, no street-sweeping notes), bd (project
    permit-days), dsig (project signals: first renovation/new/demolition permit after DUMP_WINDOW quiet days), and
    mk (distinct permits with a hauler, all purposes). Returns the signal end date."""
    end = one(con, f"SELECT DATE '{as_of}' - {DUMP_WINDOW} AS d")["d"].isoformat()
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE dmp AS
        SELECT permit_no, address_key AS k, min(start_date) AS d, first(hauler ORDER BY row_id) AS hauler,
            bool_or(purpose_sweep) AS sweep
        FROM dumpster_permits
        WHERE issue_date IS NOT NULL AND milestone NOT IN ('Cancelled', 'Denied') AND address_key IS NOT NULL
          AND start_date <= DATE '{as_of}'
        GROUP BY permit_no, address_key
    """)
    con.execute("""
        CREATE OR REPLACE TEMP TABLE mk AS
        SELECT permit_no, min(d) AS d, first(hauler ORDER BY d, k) AS hauler FROM dmp
        WHERE hauler IS NOT NULL GROUP BY permit_no
    """)
    ensure_project_permits(con)
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE dsig AS
        SELECT k, d, ptype, cost, pid, {_cost_band("cost")} AS cost_band FROM (
          SELECT k, d, ptype, cost, pid, lag(d) OVER (PARTITION BY k ORDER BY d) AS prev FROM bd
        ) WHERE (prev IS NULL OR d - prev > {DUMP_WINDOW}) AND d BETWEEN DATE '{start}' AND DATE '{end}'
    """)
    return end


def dumpster_conversion(con, start: str, end: str) -> dict:
    w = DUMP_WINDOW
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE dsig_x AS
        SELECT s.k, s.d, s.ptype, s.cost, s.cost_band, s.pid, year(s.d) AS yr,
          min(t.d - s.d) FILTER (WHERE t.d > s.d AND t.d <= s.d + {w}) AS days_after,
          coalesce(bool_or(t.d > s.d - {2 * w} AND t.d <= s.d - {w}), false) AS earlier_window,
          min(t.d) FILTER (WHERE t.d >= s.d - {w} AND t.d <= s.d + {w}) AS first_near
        FROM dsig s LEFT JOIN dmp t ON t.k = s.k AND NOT t.sweep AND t.d > s.d - {2 * w} AND t.d <= s.d + {w}
        GROUP BY s.k, s.d, s.ptype, s.cost, s.cost_band, s.pid
    """)
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE dctl_pool AS
        SELECT a.k, qd.q AS d, year(qd.q) AS yr FROM (SELECT DISTINCT k FROM bd) a
        CROSS JOIN (SELECT unnest(generate_series(DATE '{start}', DATE '{end}', INTERVAL 3 MONTH))::DATE AS q) qd
        WHERE NOT EXISTS (SELECT 1 FROM bd b WHERE b.k = a.k AND b.d > qd.q - 365 AND b.d <= qd.q + 365)
    """)
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE dctl_x AS
        SELECT c.yr, count(*) AS n,
          count(*) FILTER (WHERE EXISTS (SELECT 1 FROM dmp t WHERE t.k = c.k AND NOT t.sweep
                                         AND t.d > c.d AND t.d <= c.d + {w})) AS hits
        FROM dctl_pool c GROUP BY c.yr
    """)
    ctl = {r["yr"]: (r["n"], r["hits"]) for r in q(con, "SELECT yr, n, hits FROM dctl_x")}

    def block(where: str, label: str) -> dict:
        r = one(
            con,
            f"""
            SELECT count(*) AS signals, count(days_after) AS converted, avg((days_after IS NOT NULL)::INT) AS conversion,
              avg(earlier_window::INT) AS own_earlier_window, median(days_after) AS median_days,
              quantile_cont(days_after, 0.25) AS p25_days, quantile_cont(days_after, 0.75) AS p75_days
            FROM dsig_x WHERE {where}
        """,
        )
        years = {
            y: n
            for y, n in con.execute(f"SELECT yr, count(*) FROM dsig_x WHERE {where} GROUP BY yr").fetchall()
        }
        r["control_rate"] = _std_control(ctl, years)
        r["lift_vs_control"] = r["conversion"] / r["control_rate"] if r["control_rate"] else None
        r["lift_vs_own_earlier"] = (
            r["conversion"] / r["own_earlier_window"] if r["own_earlier_window"] else None
        )
        r["label"] = label
        return r

    head = block("true", "all")
    by_type = [
        block(f"ptype = '{t}'", t) for t in ("renovation/alteration", "new construction", "demolition")
    ]
    bands = ("under $10k", "$10k-$50k", "$50k-$250k", "$250k+", "no cost reported")
    by_cost = [block(f"cost_band = '{b}'", b) for b in bands]
    by_year = []
    for y in sorted({r[0] for r in con.execute("SELECT DISTINCT yr FROM dsig_x").fetchall()}):
        r = block(f"yr = {y}", str(y))
        by_year.append(r)
    near = one(
        con,
        """
        SELECT count(first_near) AS with_dumpster_within_180_days_either_side,
          avg((first_near < d)::INT) AS dumpster_first_share,
          avg((first_near < d - 30)::INT) AS dumpster_30_days_first_share
        FROM dsig_x
    """,
    )
    sig_week = one(
        con,
        f"SELECT count(*) FILTER (WHERE d > DATE '{end}' - 364) / 52.0 AS signals_per_week, "
        f"count(*) FILTER (WHERE d > DATE '{end}' - 364 AND days_after IS NOT NULL) / 52.0 AS converted_per_week FROM dsig_x",
    )
    recall = q(
        con,
        f"""
        SELECT 'renovation, new construction or demolition permit' AS prior_permit,
          count(*) AS dumpster_permits,
          count(*) FILTER (WHERE EXISTS (SELECT 1 FROM bd b WHERE b.k = t.k AND b.d <= t.d AND b.d >= t.d - {w}))
            AS with_prior_permit
        FROM dmp t WHERE NOT t.sweep AND t.d BETWEEN DATE '{start}' AND DATE '{end}'
        UNION ALL
        SELECT 'express or easy permit (roofs, porches, small repairs)', count(*),
          count(*) FILTER (WHERE EXISTS (SELECT 1 FROM p b WHERE b.address_key = t.k AND b.issue_date <= t.d
            AND b.issue_date >= t.d - {w} AND b.permit_type IN ('PERMIT - EXPRESS PERMIT PROGRAM', 'PERMIT - EASY PERMIT PROCESS')))
        FROM dmp t WHERE NOT t.sweep AND t.d BETWEEN DATE '{start}' AND DATE '{end}'
        UNION ALL
        SELECT 'any building permit', count(*),
          count(*) FILTER (WHERE EXISTS (SELECT 1 FROM p b WHERE b.address_key = t.k AND b.issue_date <= t.d
            AND b.issue_date >= t.d - {w}))
        FROM dmp t WHERE NOT t.sweep AND t.d BETWEEN DATE '{start}' AND DATE '{end}'
    """,
    )
    for r in recall:
        r["with_prior_permit_share"] = r["with_prior_permit"] / r["dumpster_permits"]
    return {
        "head": head,
        "by_type": by_type,
        "by_cost": by_cost,
        "by_year": by_year,
        "near": near,
        "sig_week": sig_week,
        "recall": recall,
        "control_cells": sum(n for n, _ in ctl.values()),
    }


def dumpster_market(con, as_of: str) -> dict:
    """Hauler concentration over distinct dumpster permits (all purposes)."""
    by_year = q(
        con,
        """
        WITH h AS (SELECT year(d) AS y, hauler, count(*) AS n FROM mk GROUP BY y, hauler),
        r AS (SELECT *, row_number() OVER (PARTITION BY y ORDER BY n DESC, hauler) AS rn,
                sum(n) OVER (PARTITION BY y) AS tot FROM h)
        SELECT y AS year, max(tot) AS permits, count(*) AS haulers, count(*) FILTER (WHERE n >= 20) AS haulers_20_plus,
          sum(n) FILTER (WHERE rn <= 1) / max(tot) AS top1_share, sum(n) FILTER (WHERE rn <= 5) / max(tot) AS top5_share,
          sum(n) FILTER (WHERE rn <= 10) / max(tot) AS top10_share
        FROM r GROUP BY y ORDER BY y
    """,
    )
    overall = one(
        con,
        """
        WITH h AS (SELECT hauler, count(*) AS n FROM mk GROUP BY hauler),
        r AS (SELECT *, row_number() OVER (ORDER BY n DESC, hauler) AS rn, sum(n) OVER () AS tot FROM h)
        SELECT max(tot) AS permits, count(*) AS haulers, count(*) FILTER (WHERE n >= 20) AS haulers_20_plus,
          sum(n) FILTER (WHERE rn <= 1) / max(tot) AS top1_share, sum(n) FILTER (WHERE rn <= 5) / max(tot) AS top5_share,
          sum(n) FILTER (WHERE rn <= 10) / max(tot) AS top10_share, sum((n / tot) * (n / tot)) AS hhi
        FROM r
    """,
    )
    last52 = one(
        con,
        f"""
        WITH h AS (SELECT hauler, count(*) AS n FROM mk WHERE d > DATE '{as_of}' - 364 GROUP BY hauler),
        r AS (SELECT *, row_number() OVER (ORDER BY n DESC, hauler) AS rn, sum(n) OVER () AS tot FROM h)
        SELECT max(tot) AS permits, count(*) AS haulers, count(*) FILTER (WHERE n >= 20) AS haulers_20_plus,
          sum(n) FILTER (WHERE rn <= 5) / max(tot) AS top5_share, sum(n) FILTER (WHERE rn <= 10) / max(tot) AS top10_share
        FROM r
    """,
    )
    entry = one(
        con,
        f"""
        WITH f AS (SELECT hauler, min(year(d)) AS first_y, count(*) AS n FROM mk GROUP BY hauler)
        SELECT count(*) FILTER (WHERE first_y > 2016) AS haulers_first_seen_after_2016,
          count(*) FILTER (WHERE first_y >= {int(as_of[:4]) - 2}) AS haulers_first_seen_last_3_years
        FROM f
    """,
    )
    return {"by_year": by_year, "overall": overall, "last_52_weeks": last52, "entry": entry}


def dumpster_partners(con) -> dict:
    """Does the hauler on a project repeat the hauler its GC used on an earlier project? Projects = dsig signals with
    a dumpster permit in the next 180 days (hauler of the first one) and a named GC on the project's costliest permit
    (role 'gc'; 'owner as GC' is a person). Chance = the market share of the haulers that GC used before."""
    w = DUMP_WINDOW
    con.execute("""
        CREATE OR REPLACE TEMP TABLE mshare AS
        SELECT year(d) AS y, hauler, count(*) * 1.0 / sum(count(*)) OVER (PARTITION BY year(d)) AS share
        FROM mk GROUP BY year(d), hauler
    """)
    con.execute("""
        CREATE OR REPLACE TEMP TABLE dgc AS
        SELECT permit_id, first(name_key ORDER BY slot) AS gc FROM permit_parties
        WHERE role = 'gc' AND name_key <> '' GROUP BY permit_id
    """)
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE dlink AS
        SELECT s.k, s.d, s.pid, g.gc, first(t.hauler ORDER BY t.d, t.permit_no) AS hauler
        FROM dsig s JOIN dmp t ON t.k = s.k AND NOT t.sweep AND t.hauler IS NOT NULL AND t.d > s.d AND t.d <= s.d + {w}
        JOIN dgc g ON g.permit_id = s.pid GROUP BY s.k, s.d, s.pid, g.gc
    """)
    con.execute("""
        CREATE OR REPLACE TEMP TABLE dprev AS
        SELECT DISTINCT b.gc, b.k, b.d, a.hauler FROM dlink b
        JOIN dlink a ON a.gc = b.gc AND (a.d < b.d OR (a.d = b.d AND a.k < b.k))
    """)
    con.execute("""
        CREATE OR REPLACE TEMP TABLE dchance AS
        SELECT p.gc, p.k, p.d, sum(m.share) AS chance, count(*) AS haulers_before
        FROM dprev p JOIN mshare m ON m.y = year(p.d) AND m.hauler = p.hauler GROUP BY p.gc, p.k, p.d
    """)
    r = one(
        con,
        f"""
        SELECT count(*) AS linked_projects, count(DISTINCT l.gc) AS gcs,
          count(c.gc) AS with_earlier_project,
          avg(CASE WHEN c.gc IS NOT NULL THEN
                (EXISTS (SELECT 1 FROM dprev p WHERE p.gc = l.gc AND p.k = l.k AND p.d = l.d AND p.hauler = l.hauler))::INT
              END) AS repeat_partner_share,
          avg(c.chance) AS expected_by_chance_share,
          avg(CASE WHEN c.gc IS NOT NULL THEN c.haulers_before END) AS mean_haulers_used_before,
          avg((substr({HAULER_KEY.replace("hauler", "l.hauler")}, 1, 25) =
               substr(l.gc, 1, 25))::INT) AS self_hauled_share
        FROM dlink l LEFT JOIN dchance c ON c.gc = l.gc AND c.k = l.k AND c.d = l.d
    """,
    )
    r["repeat_vs_chance"] = (
        r["repeat_partner_share"] / r["expected_by_chance_share"] if r["expected_by_chance_share"] else None
    )
    conc = one(
        con,
        """
        WITH g AS (SELECT gc, hauler, count(*) AS n FROM dlink GROUP BY gc, hauler),
        t AS (SELECT gc, max(n) AS top, sum(n) AS tot, count(*) AS haulers FROM g GROUP BY gc HAVING sum(n) >= 5)
        SELECT count(*) AS gcs_with_5_plus_projects, median(top * 1.0 / tot) AS median_top_hauler_share,
          avg((top * 1.0 / tot >= 0.8)::INT) AS gcs_80_percent_one_hauler_share,
          median(haulers) AS median_haulers_per_gc
        FROM t
    """,
    )
    r.update(conc)
    return r


# --- H41: pre-opening windows -----------------------------------------------------------------------------------
def preopening(con, as_of: str) -> dict:
    """Restaurant pre-opening ('License') inspections: timing against the business license and the first routine
    inspection, the build-out permit before them, and weekly volumes."""
    ensure_project_permits(con)
    insp_asof = one(con, "SELECT max(inspection_date) AS d FROM food_inspections")["d"].isoformat()
    con.execute("""
        CREATE OR REPLACE TEMP TABLE pre AS
        SELECT license_no, min(inspection_date) AS d,
            first(address_key ORDER BY inspection_date, inspection_id) AS k,
            first(results ORDER BY inspection_date, inspection_id) AS result
        FROM food_inspections
        WHERE inspection_type = 'License' AND facility_type = 'Restaurant' AND license_no > 0
          AND inspection_date >= DATE '2016-01-01'
        GROUP BY license_no
    """)
    con.execute("""
        CREATE OR REPLACE TEMP TABLE pre_lic AS
        SELECT x.license_no, x.d, x.k, x.result, l.issue_date, l.start_date,
            (SELECT min(f.inspection_date) FROM food_inspections f
             WHERE f.license_no = x.license_no AND f.inspection_type = 'Canvass' AND f.inspection_date > x.d) AS canvass,
            (SELECT min(f.inspection_date) FROM food_inspections f
             WHERE f.license_no = x.license_no AND f.inspection_type = 'License Re-Inspection'
               AND f.inspection_date > x.d) AS reinspect
        FROM pre x JOIN (
            SELECT license_id, min(issue_date) AS issue_date, min(start_date) AS start_date
            FROM biz_license_history WHERE application_type = 'ISSUE' GROUP BY license_id
        ) l ON l.license_id = x.license_no::VARCHAR
    """)
    timing = one(
        con,
        f"""
        SELECT (SELECT count(*) FROM pre) AS restaurant_license_inspections,
          count(*) AS matched_to_issue_license,
          median(issue_date - d) AS median_days_to_issue, quantile_cont(issue_date - d, 0.25) AS p25_days_to_issue,
          quantile_cont(issue_date - d, 0.75) AS p75_days_to_issue,
          avg((issue_date >= d)::INT) AS inspected_before_issue_share,
          avg((result = 'Pass' OR result = 'Pass w/ Conditions')::INT) AS first_inspection_pass_share,
          avg((reinspect IS NOT NULL)::INT) AS reinspected_share,
          median(reinspect - d) FILTER (WHERE reinspect IS NOT NULL) AS median_days_to_reinspection
        FROM pre_lic WHERE d <= DATE '{insp_asof}' - 540
    """,
    )
    canvass = one(
        con,
        f"""
        SELECT count(canvass) AS with_routine_inspection, median(canvass - d) AS median_days_to_routine,
          quantile_cont(canvass - d, 0.25) AS p25_days_to_routine, quantile_cont(canvass - d, 0.75) AS p75_days_to_routine
        FROM pre_lic WHERE d <= DATE '{insp_asof}' - 540
    """,
    )
    buildout = one(
        con,
        f"""
        WITH x AS (
          SELECT s.license_no, s.d, max(b.d) AS permit_d
          FROM pre s LEFT JOIN bd b ON b.k = s.k AND b.d < s.d AND b.d >= s.d - 365
          WHERE s.d >= DATE '2016-01-01' AND s.d <= DATE '{as_of}' GROUP BY s.license_no, s.d
        )
        SELECT count(*) AS inspections, count(permit_d) AS with_permit_in_prior_365_days,
          count(permit_d) * 1.0 / count(*) AS with_permit_share,
          median(d - permit_d) AS median_days_from_permit, quantile_cont(d - permit_d, 0.25) AS p25_days_from_permit,
          quantile_cont(d - permit_d, 0.75) AS p75_days_from_permit
        FROM x
    """,
    )
    weekly = one(
        con,
        f"""
        SELECT count(*) FILTER (WHERE facility_type = 'Restaurant') / 52.0 AS restaurant_per_week,
          count(*) / 52.0 AS all_facilities_per_week,
          avg((results = 'Fail')::INT) FILTER (WHERE facility_type = 'Restaurant') AS restaurant_fail_share
        FROM food_inspections
        WHERE inspection_type = 'License' AND inspection_date > DATE '{insp_asof}' - 364
          AND inspection_date <= DATE '{insp_asof}'
    """,
    )
    new_sites = one(
        con,
        """
        SELECT count(*) FILTER (WHERE d > (SELECT max(issue_date) FROM biz_license_history) - 364) / 52.0
            AS new_business_sites_per_week,
          count(*) FILTER (WHERE d > (SELECT max(issue_date) FROM biz_license_history) - 364 AND grp = 'food & drink') / 52.0
            AS new_food_sites_per_week
        FROM nsite
    """,
    )
    return {
        "inspection_as_of": insp_asof,
        "timing": timing,
        "routine": canvass,
        "buildout": buildout,
        "weekly": weekly,
        "new_sites": new_sites,
    }
