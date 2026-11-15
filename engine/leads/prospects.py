"""Our own lead list: Chicago contractors to pitch Brickline to, from their permit activity.

    uv run python -m engine.leads.prospects --trades porch masonry      # writes data/prospects-<date>.csv

Ranks contractors who are active enough to need steady work but not so large that they already have a
sales team: the sweet spot is roughly 3–60 permitted jobs a year. Contact fields are left for research;
nothing here is guessed.
"""

from __future__ import annotations

import argparse
import csv
import sys
from datetime import date
from pathlib import Path

import duckdb

from engine.leads.snapshot import TRADES, title
from engine.score.signals import prepare_base, q

DB = Path("data/warehouse.duckdb")


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
        )
        SELECT x.name_key, any_value(x.name_raw) AS name,
          count(DISTINCT x.id) FILTER (WHERE x.issue_date > DATE '{today}' - INTERVAL 365 DAY) AS jobs_12m,
          count(DISTINCT x.id) FILTER (WHERE x.issue_date <= DATE '{today}' - INTERVAL 365 DAY) AS jobs_prev_12m,
          median(x.reported_cost) FILTER (WHERE x.reported_cost > 0) AS median_job,
          max(x.issue_date) AS last_job,
          {won_sql} AS violation_driven_jobs,
          list(DISTINCT ca.name)[:4] AS areas
        FROM x LEFT JOIN community_areas ca ON ca.community_area = x.community_area
        GROUP BY x.name_key
        HAVING jobs_12m BETWEEN 3 AND 60
        ORDER BY violation_driven_jobs DESC, jobs_12m DESC
    """,
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--trades", nargs="+", default=["porch", "masonry"], choices=list(TRADES))
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()
    con = duckdb.connect(str(DB), read_only=True)
    prepare_base(con)
    today = con.execute("SELECT max(issue_date) FROM permits").fetchone()[0]
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
    n = 0
    with out.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for trade in args.trades:
            for r in prospects(con, trade, today):
                w.writerow(
                    {
                        "trade": trade,
                        "company": title(r["name"]),
                        "jobs_12m": r["jobs_12m"],
                        "jobs_prev_12m": r["jobs_prev_12m"],
                        "median_job": round(r["median_job"] or 0),
                        "last_job": r["last_job"],
                        "violation_driven_jobs": r["violation_driven_jobs"],
                        "areas": "; ".join(a for a in (r["areas"] or []) if a),
                        "status": "not contacted",
                    }
                )
                n += 1
    print(f"wrote {out}: {n} contractors")
    return 0


if __name__ == "__main__":
    sys.exit(main())
