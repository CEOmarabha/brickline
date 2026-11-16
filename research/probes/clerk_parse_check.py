"""Summary and spot-check of the City Clerk zoning reclassification table (`zoning_changes`).

    uv run python research/probes/clerk_parse_check.py

Writes research/findings/clerk-zoning-<date>.md: table size, date ranges, parse rates (share of matters with a
parsed street address, by year), the districts that titles state, and two deterministic samples of 20 parsed
matters (ordered by an md5 of the matter id) with the title next to what the parser extracted, for hand-checking.
The sampling does not depend on DuckDB row order, so the file is byte-stable for the same warehouse.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path

import duckdb

DB = Path("data/warehouse.duckdb")
OUT = Path("research/findings")
SAMPLE = 20


def fmt_pct(x: float) -> str:
    return f"{100 * x:.1f}%"


def main() -> int:
    con = duckdb.connect(str(DB), read_only=True)
    one = lambda sql: con.execute(sql).fetchone()  # noqa: E731
    rows, matters, parsed_matters, addr_rows = one(
        """SELECT count(*), count(DISTINCT matter_id), count(DISTINCT matter_id) FILTER (WHERE address_key IS NOT NULL),
             count(address_key) FROM zoning_changes"""
    )
    first_intro, last_intro, first_pass, last_pass = one(
        "SELECT min(intro_date) FILTER (WHERE intro_date >= DATE '2012-01-01'), max(intro_date), min(passed_date), "
        "max(passed_date) FROM zoning_changes"
    )
    projects = one(
        "SELECT count(DISTINCT coalesce(nullif(upper(app_no), 'TBD'), matter_id)) FROM zoning_changes"
    )[0]
    stated = one(
        "SELECT count(DISTINCT matter_id) FILTER (WHERE from_district IS NOT NULL), "
        "count(DISTINCT matter_id) FILTER (WHERE planned_development), "
        "count(DISTINCT matter_id) FILTER (WHERE type1) FROM zoning_changes"
    )
    by_status = con.execute(
        """SELECT sub_status, count(DISTINCT matter_id) FROM zoning_changes GROUP BY 1 ORDER BY 2 DESC, 1"""
    ).fetchall()
    by_year = con.execute(
        """SELECT file_year, count(DISTINCT matter_id) AS matters,
             count(DISTINCT matter_id) FILTER (WHERE address_key IS NOT NULL) AS parsed,
             count(DISTINCT matter_id) FILTER (WHERE passed) AS passed
           FROM zoning_changes GROUP BY 1 ORDER BY 1"""
    ).fetchall()
    multi = one(
        """SELECT count(*), max(n) FROM (SELECT matter_id, count(address_key) AS n FROM zoning_changes
           GROUP BY 1 HAVING count(address_key) > 1)"""
    )
    unparsed = con.execute(
        """SELECT title FROM zoning_changes WHERE address_key IS NULL GROUP BY title ORDER BY md5(title) LIMIT 12"""
    ).fetchall()
    zd = one(
        """SELECT count(*), count(DISTINCT app_no) FILTER (WHERE app_no IS NOT NULL) FROM zoning_districts"""
    )
    matched = one(
        """WITH m AS (SELECT DISTINCT matter_id, record_no, upper(app_no) AS app_no FROM zoning_changes
                     WHERE passed AND intro_date >= DATE '2012-01-01')
           SELECT count(*), count(*) FILTER (WHERE EXISTS (SELECT 1 FROM zoning_districts z
                  WHERE z.app_no = m.app_no OR z.clerk_docn = m.record_no)) FROM m"""
    )
    sample_sql = f"""
        SELECT matter_id, any_value(title) AS title, string_agg(address_key || CASE WHEN addr_num_to IS NOT NULL
               THEN ' (to ' || addr_num_to || ')' ELSE '' END, '; ' ORDER BY addr_idx) AS parsed,
          any_value(app_no) AS app_no, any_value(intro_date) AS intro, any_value(sub_status) AS status,
          any_value(final_action_date) AS final_date
        FROM zoning_changes WHERE address_key IS NOT NULL GROUP BY matter_id
        ORDER BY md5(matter_id) LIMIT {2 * SAMPLE}
    """
    sample = con.execute(sample_sql).fetchall()
    today = os.environ.get("SIGNAL_LAB_DATE") or datetime.now(UTC).date().isoformat()
    L = [
        f"# City Clerk zoning reclassifications: table summary and parse check ({today})",
        "",
        'Source: `https://api.chicityclerkelms.chicago.gov/matter` (phrase search "Zoning Reclassification Map No" '
        "by `fileYear` 2012 onward), parsed by `engine/collect/clerk.py` into the warehouse table `zoning_changes`. "
        "Reproduce: `uv run python -m engine.warehouse sync --only clerk adu_preapprovals zoning_districts`, "
        "`build`, then this script.",
        "",
        "## Size and range",
        "",
        f"- Rows (one per matter and address): {rows:,}; matters: {matters:,}; distinct applications (App No., or the "
        f"matter itself when there is none or it is TBD): {projects:,}.",
        f"- Introduction dates from {first_intro} (matters filed from 2012 on; a handful were introduced earlier and "
        f"substituted later) to {last_intro} (the API lists future Council meeting dates for matters just filed); "
        f"passage dates {first_pass} to {last_pass}.",
        f"- **Parse rate:** {parsed_matters:,} of {matters:,} matters ({fmt_pct(parsed_matters / matters)}) have at "
        f"least one parsed street address ({addr_rows:,} address rows; {multi[0]:,} matters list several addresses, up "
        f"to {multi[1]}). The rest are intersections, areas or free text (examples below).",
        f'- Titles that state districts ("RS3 to RT4"): {stated[0]} matters. Planned Development named in the title: '
        f"{stated[1]}. App No. with a T1 suffix: {stated[2]:,}. District information is otherwise not in the title "
        f"or the metadata; the ordinance PDFs are scanned images, so the lab reads the target district of passed "
        f"ordinances from today's zoning map ({zd[0]:,} polygons, {zd[1]:,} application numbers): "
        f"{matched[1]:,} of {matched[0]:,} passed matters since 2012 ({fmt_pct(matched[1] / matched[0])}) match by "
        f"application number or Clerk record number.",
        "",
        "## Status and year",
        "",
        "| Status (`subStatus`) | Matters |",
        "| --- | --- |",
        *[f"| {s} | {n:,} |" for s, n in by_status],
        "",
        "| File year | Matters | With parsed address | Passed (incl. as substitute) |",
        "| --- | --- | --- | --- |",
        *[f"| {y} | {m:,} | {p:,} ({fmt_pct(p / m)}) | {ps:,} |" for y, m, p, ps in by_year],
        "",
        "## Titles without a parsed address (12, deterministic sample)",
        "",
        *[f"- {t[0]}" for t in unparsed],
        "",
        f"## Hand-check samples ({SAMPLE} + {SAMPLE} parsed matters ordered by md5 of the matter id)",
        "",
        "Sample A (the first 20) was read before the final parser fixes and re-read after them; sample B (the next 20) "
        "was read only after. Results are in `docs/13-signal-lab.md`.",
    ]
    for label, part in (("A", sample[:SAMPLE]), ("B", sample[SAMPLE:])):
        L += [
            "",
            f"### Sample {label}",
            "",
            "| # | Title | Parsed address keys (first number kept; range end in parentheses) | App No. | Introduced | Status | Final action |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
        for i, (_, title, parsed, app, intro, status, final) in enumerate(part, 1):
            L.append(f"| {i} | {title} | {parsed} | {app or ''} | {intro} | {status} | {final or ''} |")
    L.append("")
    path = OUT / f"clerk-zoning-{today}.md"
    OUT.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(L))
    print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
