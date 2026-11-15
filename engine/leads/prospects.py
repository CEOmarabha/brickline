"""Our own lead list: Chicago contractors to pitch Brickline to, from their permit activity.

    uv run python -m engine.leads.prospects --trades porch masonry      # writes data/prospects-<date>.csv

Also always writes web/data/prospects.json (all of PROSPECT_TRADES, whatever --trades says), which the
app's /prospects pages read.

Ranks contractors who are active enough to need steady work but not so large that they already have a
sales team: the sweet spot is roughly 3–60 permitted jobs a year. Contact fields are left for research;
nothing here is guessed.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from datetime import date
from pathlib import Path

import duckdb

from engine.leads.snapshot import TRADES, title
from engine.score.signals import prepare_base, q

DB = Path("data/warehouse.duckdb")
JSON_OUT = Path("web/data/prospects.json")
PROSPECT_TRADES = ("porch", "masonry", "roofing", "plumbing", "electrical")
MIN_JOBS, MAX_JOBS = 3, 60
MAX_AREAS = 4


def slug(trade: str, name_key: str) -> str:
    return f"{trade}-{re.sub(r'[^a-z0-9]+', '-', name_key.lower()).strip('-')}"


def prospects(con, trade: str, today: date) -> list[dict]:
    t = TRADES[trade]
    vt = t["violation"]
    won_sql = (
        f"""count(DISTINCT x.id) FILTER (WHERE EXISTS (
              SELECT 1 FROM violations v WHERE v.address_key = x.address_key AND v.t_{vt}
                AND v.violation_date BETWEEN x.issue_date - INTERVAL 365 DAY AND x.issue_date))"""
        if vt
        else "0"
    )
    return q(
        con,
        f"""
        WITH x AS (
          SELECT p.id, p.issue_date, p.reported_cost, p.community_area, p.address_key, pp.name_key, pp.name_raw
          FROM p JOIN permit_parties pp ON pp.permit_id = p.id AND pp.role = '{t["role"]}'
          WHERE p.t_{t["permit"]} AND pp.name_key <> '' AND p.issue_date > DATE '{today}' - INTERVAL 730 DAY
        ), top AS (
          SELECT name_key, list(community_area ORDER BY n DESC, community_area)[:{MAX_AREAS}] AS area_ids
          FROM (SELECT name_key, community_area, count(DISTINCT id) AS n FROM x
                WHERE community_area IS NOT NULL GROUP BY ALL)
          GROUP BY name_key
        )
        SELECT x.name_key, first(x.name_raw ORDER BY x.issue_date DESC, x.id) AS name,
          count(DISTINCT x.id) FILTER (WHERE x.issue_date > DATE '{today}' - INTERVAL 365 DAY) AS jobs_12m,
          count(DISTINCT x.id) FILTER (WHERE x.issue_date <= DATE '{today}' - INTERVAL 365 DAY) AS jobs_prev_12m,
          median(x.reported_cost) FILTER (WHERE x.reported_cost > 0) AS median_job,
          max(x.issue_date) AS last_job,
          {won_sql} AS violation_driven_jobs,
          any_value(top.area_ids) AS area_ids
        FROM x LEFT JOIN top ON top.name_key = x.name_key
        GROUP BY x.name_key
        HAVING jobs_12m BETWEEN {MIN_JOBS} AND {MAX_JOBS}
        ORDER BY violation_driven_jobs DESC, jobs_12m DESC, name, x.name_key
    """,
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--trades", nargs="+", default=["porch", "masonry"], choices=list(TRADES), help="trades in the CSV"
    )
    ap.add_argument("--out", type=Path, default=None, help="CSV path (default data/prospects-<date>.csv)")
    ap.add_argument("--json", type=Path, default=JSON_OUT, help=f"JSON path for the app (default {JSON_OUT})")
    args = ap.parse_args()
    con = duckdb.connect(str(DB), read_only=True)
    prepare_base(con)
    today = con.execute("SELECT max(issue_date) FROM permits").fetchone()[0]
    area_names = {
        r["community_area"]: r["name"] for r in q(con, "SELECT community_area, name FROM community_areas")
    }
    out = args.out or Path(f"data/prospects-{today}.csv")
    fields = [
        "trade",
        "company",
        "jobs_12m",
        "jobs_prev_12m",
        "median_job",
        "last_job",
        "violation_driven_jobs",
        "areas",
        "website",
        "phone",
        "email",
        "contact_name",
        "status",
        "notes",
    ]
    cache: dict[str, list[dict]] = {}

    def rows_for(trade: str) -> list[dict]:
        if trade not in cache:
            cache[trade] = prospects(con, trade, today)
        return cache[trade]

    n = 0
    with out.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for trade in args.trades:
            for r in rows_for(trade):
                w.writerow(
                    {
                        "trade": trade,
                        "company": title(r["name"]),
                        "jobs_12m": r["jobs_12m"],
                        "jobs_prev_12m": r["jobs_prev_12m"],
                        "median_job": round(r["median_job"] or 0),
                        "last_job": r["last_job"],
                        "violation_driven_jobs": r["violation_driven_jobs"],
                        "areas": "; ".join(area_names[a] for a in (r["area_ids"] or []) if a in area_names),
                        "status": "not contacted",
                    }
                )
                n += 1
    print(f"wrote {out}: {n} contractors")

    items = []
    counts = {}
    for trade in PROSPECT_TRADES:
        rows = rows_for(trade)
        counts[trade] = len(rows)
        for r in rows:
            items.append(
                {
                    "id": slug(trade, r["name_key"]),
                    "trade": trade,
                    "company": title(r["name"]),
                    "jobs12m": r["jobs_12m"],
                    "jobsPrev12m": r["jobs_prev_12m"],
                    "medianJob": round(r["median_job"] or 0),
                    "lastJob": r["last_job"].isoformat(),
                    "violationDrivenJobs": r["violation_driven_jobs"],
                    "areaIds": [a for a in (r["area_ids"] or []) if a is not None],
                }
            )
    args.json.parent.mkdir(parents=True, exist_ok=True)
    payload = {"generatedFor": today.isoformat(), "prospects": items}
    args.json.write_text(json.dumps(payload, separators=(",", ":"), ensure_ascii=False) + "\n")
    print(f"wrote {args.json}: {len(items)} prospects {counts} ({args.json.stat().st_size / 1024:.0f} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
