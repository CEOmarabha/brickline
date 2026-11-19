"""Private outreach lists: block-party hosts and repeat event food and drink vendors (D-027).

    uv run python -m engine.leads.hosts

Block-party hosts are private persons, so these lists go only to data/private/ (gitignored, never shipped with the
app) and the findings file holds counts. Two lists:

  * block-party hosts: parties starting in the next 90 days (host name and mailing address from the CDOT
    application), and blocks likely to hold one next season (a party in at least 2 of the last 3 seasons and no
    permit yet), with the month of their last party. The rule is backtested on the season before.
  * repeat event vendors: holders of Special Event Food/Liquor licenses in at least 2 of the last 3 years, with
    their usual month and the license address. On the 2026-11-17 data 370 of 393 are restaurants, food trucks and
    bars that sell at fairs (vendors to recruit and sell the event calendar to); 23 are organizers.

Every row carries the services that event usually buys (engine/leads/lifecycles.py) and the allowed channel: mail
or door hanger to anyone; a manual call or text only to a number from a provider whose terms allow marketing,
scrubbed against the National Do Not Call Registry and our own opt-out list (docs/14 §8).
"""

from __future__ import annotations

import argparse
import csv
from datetime import date
from pathlib import Path

from engine import db
from engine.leads.lifecycles import LIFECYCLES, VENDORS

PRIVATE = Path("data/private")
FINDINGS = Path("research/findings")
UPCOMING_DAYS = 90
CHANNEL = "Letter or door hanger; call/text only after skip trace + DNC scrub"


def services_for(lifecycle_id: str) -> str:
    lc = next(x for x in LIFECYCLES if x.id == lifecycle_id)
    return "; ".join(f"{sv.name} ({VENDORS[sv.vendor][0]})" for st in lc.stages for sv in st.services)


def seasons(as_of: date) -> tuple[int, list[int]]:
    """Season to predict (next summer once September has passed) and the three seasons before it."""
    target = as_of.year + 1 if as_of.month >= 9 else as_of.year
    return target, [target - 3, target - 2, target - 1]


def backtest(con, target: int) -> dict:
    """Of blocks with parties in k of the 3 seasons before `target`, the share that held one in `target`."""
    past = [target - 3, target - 2, target - 1]
    rows = con.execute(f"""
        WITH b AS (
          SELECT block_key, count(DISTINCT year(start_date)) FILTER (WHERE year(start_date) IN ({",".join(map(str, past))})) AS k,
            bool_or(year(start_date) = {target}) AS hit
          FROM block_party_hosts WHERE block_key IS NOT NULL GROUP BY 1
        )
        SELECT k, count(*) AS blocks, avg(hit::INT) AS rate FROM b WHERE k > 0 GROUP BY 1 ORDER BY 1
    """).fetchall()
    return {int(k): {"blocks": n, "repeatRate": round(r, 4)} for k, n, r in rows}


def block_lists(con, as_of: date) -> tuple[list[dict], list[dict]]:
    target, past = seasons(as_of)
    upcoming = con.execute(f"""
        SELECT start_date, block, ward, host_name, host_street, host_city, host_state, host_zip, permit_no
        FROM block_party_hosts
        WHERE start_date > DATE '{as_of}' AND start_date <= DATE '{as_of}' + INTERVAL {UPCOMING_DAYS} DAY
          AND status IS DISTINCT FROM 'Cancelled'
        ORDER BY start_date, block, permit_no
    """).fetchall()
    likely = con.execute(f"""
        WITH b AS (
          SELECT block_key,
            count(DISTINCT year(start_date)) FILTER (WHERE year(start_date) IN ({",".join(map(str, past))})) AS k,
            bool_or(year(start_date) >= {target}) AS filed,
            max(start_date) FILTER (WHERE year(start_date) < {target}) AS last_date
          FROM block_party_hosts WHERE block_key IS NOT NULL GROUP BY 1
        )
        SELECT b.k, b.last_date, h.block, h.ward, h.host_name, h.host_street, h.host_city, h.host_state, h.host_zip
        FROM b JOIN block_party_hosts h ON h.block_key = b.block_key AND h.start_date = b.last_date
        WHERE b.k >= 2 AND NOT b.filed
        QUALIFY row_number() OVER (PARTITION BY b.block_key ORDER BY h.permit_no DESC) = 1
        ORDER BY month(b.last_date), day(b.last_date), h.block
    """).fetchall()
    cols_u = (
        "date",
        "block",
        "ward",
        "host_name",
        "host_street",
        "host_city",
        "host_state",
        "host_zip",
        "permit_no",
    )
    cols_l = ("past_seasons", "last_party", "block", "ward", "host_name", "host_street", "host_city", "host_state", "host_zip")  # fmt: skip
    return [dict(zip(cols_u, r, strict=True)) for r in upcoming], [
        dict(zip(cols_l, r, strict=True)) for r in likely
    ]


def organizations(con, as_of: date) -> list[dict]:
    y = as_of.year
    rows = con.execute(f"""
        SELECT account_number, any_value(legal_name ORDER BY start_date DESC) AS legal_name,
          any_value(dba ORDER BY start_date DESC) AS dba,
          any_value(address ORDER BY start_date DESC) AS address,
          count(DISTINCT year(start_date)) AS years,
          mode(month(start_date)) AS usual_month,
          string_agg(DISTINCT license_description, ', ' ORDER BY license_description) AS licenses,
          max(start_date) AS last_event
        FROM biz_license_history
        WHERE license_description IN ('Special Event Food', 'Special Event Liquor')
          AND year(start_date) BETWEEN {y - 2} AND {y}
        GROUP BY 1 HAVING count(DISTINCT year(start_date)) >= 2
        ORDER BY usual_month, legal_name, account_number
    """).fetchall()
    cols = ("account", "legal_name", "dba", "address", "years", "usual_month", "licenses", "last_event")
    return [dict(zip(cols, r, strict=True)) for r in rows]


def write_csv(path: Path, rows: list[dict], extra: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=[*(rows[0].keys() if rows else []), *extra])
        w.writeheader()
        for r in rows:
            w.writerow({**r, **extra})


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.parse_args()
    con = db.connect()
    as_of = con.execute(
        "SELECT max(processed_date) FROM block_party_hosts WHERE processed_date <= current_date"
    ).fetchone()[0]
    target, past = seasons(as_of)
    upcoming, likely = block_lists(con, as_of)
    orgs = organizations(con, as_of)
    bt = backtest(con, target - 1)
    block_extra = {"services": services_for("block_party"), "channel": CHANNEL}
    write_csv(PRIVATE / f"block-party-upcoming-{as_of}.csv", upcoming, block_extra)
    write_csv(PRIVATE / f"block-party-likely-{target}-{as_of}.csv", likely, block_extra)
    write_csv(
        PRIVATE / f"repeat-event-vendors-{as_of}.csv",
        orgs,
        {
            "services": "Sells food or drink at events: offer the event calendar and bookings",
            "channel": "Business phone, email or website; letter",
        },
    )
    lines = [
        f"# Private outreach lists ({as_of})",
        "",
        "Counts only; the lists themselves are in `data/private/` (gitignored). "
        "Reproduce with `uv run python -m engine.leads.hosts`.",
        "",
        f"- Block parties starting in the next {UPCOMING_DAYS} days: {len(upcoming):,} (host name and mailing address "
        f"on {sum(1 for r in upcoming if r['host_street']):,}).",
        f"- Blocks likely to hold a party in {target} (parties in at least 2 of {past[0]}-{past[-1]}, no permit yet): "
        f"{len(likely):,}.",
        f"- Repeat event food and drink vendors (Special Event Food/Liquor licenses in 2+ of the last 3 years): "
        f"{len(orgs):,} (most are restaurants, food trucks and bars).",
        "",
        f"## Backtest: share of blocks holding a party in {target - 1}, by how many of {target - 4}-{target - 2} "
        "they held one",
        "",
        "| Seasons with a party (of 3) | Blocks | Held one again |",
        "| ---: | ---: | ---: |",
        *[f"| {k} | {v['blocks']:,} | {v['repeatRate'] * 100:.1f}% |" for k, v in sorted(bt.items())],
        "",
    ]
    FINDINGS.mkdir(parents=True, exist_ok=True)
    (FINDINGS / f"private-lists-{as_of}.md").write_text("\n".join(lines))
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
