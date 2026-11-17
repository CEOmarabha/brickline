"""Measure what Chicago's public data can and cannot tell a contractor.

Answers the questions the plan depends on, using live data:
  * How many meaningful construction projects appear per week?
  * By the time a permit is issued, are the trade contractors already named?
  * How long between application and issue (i.e. how "early" is a permit)?
  * Which general contractors dominate (relationship-mapping value)?
  * How much volume do earlier / intent-heavy signals carry
    (building violations, new business licenses, restaurant license inspections)?

Standard library only. Usage:
    python3 research/probes/chicago_signal_probe.py [--days 90] [--out research/findings]
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta
from pathlib import Path

PORTAL = "https://data.cityofchicago.org/resource"
PERMITS = "ydr8-5enu"
VIOLATIONS = "22u3-xenr"
LICENSES = "r5kz-chrr"
FOOD_INSPECTIONS = "4ijn-s7e5"

MAJOR_TYPES = ("PERMIT - NEW CONSTRUCTION", "PERMIT - RENOVATION/ALTERATION")
MAJOR_MIN_COST = 100_000

# Contact-type substrings -> trade. Chicago lists licensed trade contractors on the permit.
TRADE_CONTACTS = {
    "general_contractor": ("GENERAL CONTRACTOR",),
    "electrical": ("ELECTRICAL",),
    "plumbing": ("PLUMB",),
    "masonry": ("MASONRY",),
    "hvac": ("VENTILATION", "REFRIGERATION"),
    "architect": ("ARCHITECT",),
    "owner": ("OWNER",),
}
SUB_TRADES = ("electrical", "plumbing", "hvac", "masonry")

VIOLATION_TRADES = {
    "roofing": ("ROOF", "GUTTER"),
    "masonry_tuckpointing": ("MASONRY", "TUCKPOINT", "BRICK", "PARAPET", "CHIMNEY"),
    "porch_deck_stairs": ("PORCH", "STAIR", "DECK", "BALCON"),
    "windows_doors": ("WINDOW", "DOOR"),
    "plumbing": ("PLUMB", "WATER HEATER", "DRAIN", "SEWER", "FIXTURE"),
    "heating_hvac": ("HEAT", "FURNACE", "BOILER", "VENT"),
    "electrical": ("ELECTRIC", "WIRING", "OUTLET", "LIGHT"),
    "pest": ("RODENT", "INSECT", "ROACH", "BED BUG", "PEST"),
    "smoke_co_detectors": ("SMOKE", "CARBON MONOXIDE"),
}


def fetch(dataset: str, **params: str) -> list[dict]:
    query = urllib.parse.urlencode({f"${k}": v for k, v in params.items()})
    url = f"{PORTAL}/{dataset}.json?{query}"
    for attempt in range(4):
        try:
            with urllib.request.urlopen(url, timeout=120) as resp:
                return json.load(resp)
        except (OSError, ValueError) as exc:  # network hiccups on a public portal are common
            if attempt == 3:
                raise RuntimeError(f"failed after 4 attempts: {url}") from exc
            time.sleep(4 * 2**attempt)
    raise AssertionError("unreachable")


def fetch_all(dataset: str, page: int = 50_000, **params: str) -> list[dict]:
    rows: list[dict] = []
    offset = 0
    while True:
        batch = fetch(dataset, limit=str(page), offset=str(offset), **params)
        rows.extend(batch)
        if len(batch) < page:
            return rows
        offset += page


def pct(n: int, d: int) -> float:
    return round(100.0 * n / d, 1) if d else 0.0


def quantiles(values: list[float]) -> dict:
    if not values:
        return {}
    values = sorted(values)
    q = statistics.quantiles(values, n=20, method="inclusive") if len(values) > 1 else values * 19
    return {"p25": q[4], "median": statistics.median(values), "p75": q[14], "p90": q[17]}


def contacts(row: dict) -> list[tuple[str, str]]:
    out = []
    for i in range(1, 16):
        t, n = row.get(f"contact_{i}_type"), row.get(f"contact_{i}_name")
        if t or n:
            out.append(((t or "").upper(), (n or "").strip().upper()))
    return out


def probe_permits(since: str, days: int) -> dict:
    types_sql = ",".join(f"'{t}'" for t in MAJOR_TYPES)
    by_type = fetch(
        PERMITS,
        select="permit_type, count(*) as n, sum(reported_cost) as cost",
        where=f"issue_date >= '{since}'",
        group="permit_type",
        order="n DESC",
    )
    by_work = fetch(
        PERMITS,
        select="work_type, count(*) as n",
        where=f"issue_date >= '{since}'",
        group="work_type",
        order="n DESC",
        limit="40",
    )
    major = fetch_all(
        PERMITS,
        where=f"issue_date >= '{since}' AND permit_type in({types_sql}) "
        f"AND reported_cost >= {MAJOR_MIN_COST}",
        order="issue_date DESC",
    )

    n = len(major)
    trade_named = Counter()
    gc_jobs: dict[str, list[float]] = defaultdict(list)
    sub_jobs: dict[str, Counter] = {t: Counter() for t in SUB_TRADES}
    pairs: dict[str, dict[str, Counter]] = defaultdict(lambda: defaultdict(Counter))
    proc_days, costs = [], []
    complete = Counter()
    for r in major:
        cs = contacts(r)
        for trade, needles in TRADE_CONTACTS.items():
            if any(any(nd in t for nd in needles) for t, _ in cs):
                trade_named[trade] += 1
        gcs = {name for t, name in cs if "GENERAL CONTRACTOR" in t and "OWNER" not in t and name}
        for name in gcs:
            gc_jobs[name].append(float(r.get("reported_cost") or 0))
        for trade in SUB_TRADES:
            subs = {
                name
                for t, name in cs
                if name and any(nd in t for nd in TRADE_CONTACTS[trade]) and "OWNER" not in t
            }
            for s in subs:
                sub_jobs[trade][s] += 1
                for g in gcs:
                    pairs[g][trade][s] += 1
        if r.get("processing_time"):
            proc_days.append(float(r["processing_time"]))
        cost = float(r.get("reported_cost") or 0)
        costs.append(cost)
        complete["reported_cost"] += cost > 0
        complete["lat_long"] += bool(r.get("latitude"))
        complete["pin"] += bool(r.get("pin_list"))
        complete["description_40_chars"] += len(r.get("work_description") or "") >= 40

    top_gcs = sorted(
        ({"name": k, "permits": len(v), "reported_value": sum(v)} for k, v in gc_jobs.items()),
        key=lambda x: (-x["permits"], -x["reported_value"]),
    )[:15]

    sub_market = {}
    for trade, counter in sub_jobs.items():
        total_jobs = sum(counter.values())
        top10 = sum(c for _, c in counter.most_common(10))
        sub_market[trade] = {
            "distinct_contractors": len(counter),
            "top10_share_pct": pct(top10, total_jobs),
            "top5": counter.most_common(5),
        }

    gc_partners = []
    for g in top_gcs[:8]:
        entry = {"gc": g["name"], "permits": g["permits"]}
        for trade in SUB_TRADES:
            entry[trade] = pairs[g["name"]][trade].most_common(3)
        gc_partners.append(entry)

    buckets = {">=100k": 0, ">=500k": 0, ">=1M": 0, ">=5M": 0}
    for c in costs:
        buckets[">=100k"] += 1
        buckets[">=500k"] += c >= 500_000
        buckets[">=1M"] += c >= 1_000_000
        buckets[">=5M"] += c >= 5_000_000

    total = sum(int(r["n"]) for r in by_type)
    return {
        "total_permits": total,
        "permits_per_week": round(total / (days / 7), 1),
        "by_permit_type": by_type,
        "by_work_type": by_work,
        "major_projects": {
            "definition": f"{' / '.join(MAJOR_TYPES)} with reported_cost >= ${MAJOR_MIN_COST:,}",
            "count": n,
            "per_week": round(n / (days / 7), 1),
            "cost_buckets": buckets,
            "days_application_to_issue": quantiles(proc_days),
            "trade_already_named_on_permit_pct": {k: pct(v, n) for k, v in trade_named.items()},
            "field_completeness_pct": {k: pct(v, n) for k, v in complete.items()},
            "distinct_general_contractors": len(gc_jobs),
            "top_general_contractors": top_gcs,
            "subcontractor_market": sub_market,
            "gc_to_sub_partners": gc_partners,
        },
    }


def probe_violations(since: str) -> dict:
    rows = fetch_all(
        VIOLATIONS,
        select="violation_description, violation_status, inspection_category, address",
        where=f"violation_date >= '{since}'",
    )
    open_rows = [r for r in rows if (r.get("violation_status") or "").upper() == "OPEN"]
    trade_counts, trade_addresses = Counter(), defaultdict(set)
    for r in open_rows:
        desc = (r.get("violation_description") or "").upper()
        for trade, needles in VIOLATION_TRADES.items():
            if any(nd in desc for nd in needles):
                trade_counts[trade] += 1
                trade_addresses[trade].add(r.get("address"))
    return {
        "violations": len(rows),
        "open_violations": len(open_rows),
        "distinct_addresses_with_open_violations": len({r.get("address") for r in open_rows}),
        "by_category": Counter(r.get("inspection_category") for r in rows).most_common(),
        "top_open_descriptions": Counter(r.get("violation_description") for r in open_rows).most_common(20),
        "open_by_trade": {
            t: {"violations": c, "distinct_addresses": len(trade_addresses[t])}
            for t, c in trade_counts.most_common()
        },
    }


def probe_licenses(since: str) -> dict:
    issued = fetch(
        LICENSES,
        select="license_description, count(*) as n",
        where=f"application_type = 'ISSUE' AND date_issued >= '{since}'",
        group="license_description",
        order="n DESC",
        limit="25",
    )
    pending = fetch(
        LICENSES,
        select="license_description, count(*) as n",
        where=f"application_type = 'ISSUE' AND date_issued IS NULL AND application_created_date >= '{since}'",
        group="license_description",
        order="n DESC",
        limit="15",
    )
    lag = fetch(
        LICENSES,
        select="application_created_date, date_issued",
        where=f"application_type = 'ISSUE' AND date_issued >= '{since}' "
        "AND application_created_date IS NOT NULL",
        limit="50000",
    )
    days = []
    for r in lag:
        try:
            a = datetime.fromisoformat(r["application_created_date"][:19])
            b = datetime.fromisoformat(r["date_issued"][:19])
            if b >= a:
                days.append((b - a).days)
        except (KeyError, ValueError):
            continue
    return {
        "new_licenses_issued": sum(int(r["n"]) for r in issued),
        "issued_by_type": issued,
        "pending_new_applications": sum(int(r["n"]) for r in pending),
        "pending_by_type": pending,
        "days_application_to_issue": quantiles(days),
    }


def probe_food(since: str) -> dict:
    rows = fetch(
        FOOD_INSPECTIONS,
        select="inspection_type, results, count(*) as n",
        where=f"inspection_date >= '{since}' AND upper(inspection_type) like 'LICENSE%'",
        group="inspection_type, results",
        order="n DESC",
    )
    return {
        "license_inspections": sum(int(r["n"]) for r in rows),
        "breakdown": rows,
    }


def render(report: dict) -> str:
    p, m = report["permits"], report["permits"]["major_projects"]
    v, lic, food = report["violations"], report["licenses"], report["food"]
    d = m["days_application_to_issue"]
    lines = [
        f"# Chicago public-data signal probe — {report['generated_on']}",
        "",
        f"Window: permits last {report['permit_window_days']} days; other signals last "
        f"{report['signal_window_days']} days. Source: City of Chicago Data Portal (Socrata). "
        "Re-run with `python3 research/probes/chicago_signal_probe.py`.",
        "",
        "## Building permits",
        "",
        f"- All issued permits: **{p['total_permits']:,}** (~{p['permits_per_week']:,}/week)",
        f"- Major projects ({m['definition']}): **{m['count']:,}** (~{m['per_week']}/week)",
        "- Value buckets: " + ", ".join(f"{k}: {v_:,}" for k, v_ in m["cost_buckets"].items()),
        f"- Days from application to issue (major): p25 {d.get('p25', 0):.0f}, median "
        f"{d.get('median', 0):.0f}, p75 {d.get('p75', 0):.0f}, p90 {d.get('p90', 0):.0f}",
        f"- Distinct general contractors on major permits: {m['distinct_general_contractors']:,}",
        "",
        "### Share of major permits where the party is already named at issue",
        "",
        "| Party | % of major permits |",
        "| --- | --- |",
    ]
    for k, val in sorted(m["trade_already_named_on_permit_pct"].items(), key=lambda x: -x[1]):
        lines.append(f"| {k} | {val}% |")
    lines += ["", "### Field completeness (major permits)", "", "| Field | % present |", "| --- | --- |"]
    for k, val in m["field_completeness_pct"].items():
        lines.append(f"| {k} | {val}% |")
    lines += [
        "",
        "### Most active general contractors (major permits)",
        "",
        "| GC | Permits | Reported value |",
        "| --- | --- | --- |",
    ]
    for g in m["top_general_contractors"]:
        lines.append(f"| {g['name']} | {g['permits']} | ${g['reported_value']:,.0f} |")
    lines += [
        "",
        "### Subcontractor market structure (major permits)",
        "",
        "| Trade | Distinct contractors | Top-10 share of jobs | Top 3 |",
        "| --- | --- | --- | --- |",
    ]
    for trade, s in m["subcontractor_market"].items():
        top3 = "; ".join(f"{name} ({c})" for name, c in s["top5"][:3])
        lines.append(f"| {trade} | {s['distinct_contractors']} | {s['top10_share_pct']}% | {top3} |")
    lines += [
        "",
        "### Which subcontractors the busiest GCs used (relationship map sample)",
        "",
        "| GC | Electrical | Plumbing | HVAC |",
        "| --- | --- | --- | --- |",
    ]

    def cell(partners: list) -> str:
        return "; ".join(f"{n} ({c})" for n, c in partners) or "—"

    for e in m["gc_to_sub_partners"]:
        lines.append(
            f"| {e['gc']} ({e['permits']}) | {cell(e['electrical'])} | "
            f"{cell(e['plumbing'])} | {cell(e['hvac'])} |"
        )
    lines += ["", "### Permits by work type (all permits)", "", "| Work type | Count |", "| --- | --- |"]
    for r in p["by_work_type"]:
        lines.append(f"| {r.get('work_type', '(blank)')} | {int(r['n']):,} |")

    lines += [
        "",
        "## Building violations (intent signal: owner is ordered to fix something)",
        "",
        f"- Violations recorded: **{v['violations']:,}**; open: **{v['open_violations']:,}** at "
        f"{v['distinct_addresses_with_open_violations']:,} distinct addresses",
        "",
        "| Trade (keyword match on open violations) | Violations | Distinct addresses |",
        "| --- | --- | --- |",
    ]
    for t, c in v["open_by_trade"].items():
        lines.append(f"| {t} | {c['violations']:,} | {c['distinct_addresses']:,} |")
    lines += ["", "Top open violation descriptions:", ""]
    for desc, c in v["top_open_descriptions"][:12]:
        lines.append(f"- {desc} — {c:,}")

    ld = lic["days_application_to_issue"]
    lines += [
        "",
        "## New business licenses (new-business signal for B2B services)",
        "",
        f"- New licenses issued: **{lic['new_licenses_issued']:,}**",
        f"- New applications still pending (filed in window, not yet issued): "
        f"**{lic['pending_new_applications']:,}**",
        f"- Days from application to issue: median {ld.get('median', 0):.0f}, p75 {ld.get('p75', 0):.0f}",
        "",
        "| License type (issued) | Count |",
        "| --- | --- |",
    ]
    for r in lic["issued_by_type"][:12]:
        lines.append(f"| {r['license_description']} | {int(r['n']):,} |")
    lines += [
        "",
        "## Restaurant license inspections (a food business about to open)",
        "",
        f"- License-type food inspections: **{food['license_inspections']:,}**",
        "",
        "| Inspection type | Result | Count |",
        "| --- | --- | --- |",
    ]
    for r in food["breakdown"][:10]:
        lines.append(f"| {r.get('inspection_type')} | {r.get('results')} | {int(r['n']):,} |")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=90, help="permit window in days")
    ap.add_argument("--signal-days", type=int, default=30, help="window for other signals")
    ap.add_argument("--out", default="research/findings")
    args = ap.parse_args()

    today = datetime.now(UTC).date()
    since_permits = (today - timedelta(days=args.days)).isoformat() + "T00:00:00"
    since_signals = (today - timedelta(days=args.signal_days)).isoformat() + "T00:00:00"

    report = {
        "generated_on": today.isoformat(),
        "permit_window_days": args.days,
        "signal_window_days": args.signal_days,
        "permits": probe_permits(since_permits, args.days),
        "violations": probe_violations(since_signals),
        "licenses": probe_licenses(since_signals),
        "food": probe_food(since_signals),
    }

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    stem = f"chicago-signal-probe-{today.isoformat()}"
    (out / f"{stem}.json").write_text(json.dumps(report, indent=2, default=str))
    (out / f"{stem}.md").write_text(render(report))
    print(f"wrote {out / stem}.md and .json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
