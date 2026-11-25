"""Daily event-lead scanner.

    uv run python -m engine.leads.event_scan

Collects public calendars (Park District, DCASE, tourism RSS, CDOT when the warehouse
exists) plus configured social/listing providers, geo-fences to Chicagoland / Milwaukee /
NW Indiana, extracts/dedups/scores, and writes web/data/event-leads.json plus a 7 AM
America/Chicago digest. Optional Postgres upsert when DATABASE_URL is set.

    uv run python -m engine.leads.event_scan --public-only
    uv run python -m engine.leads.event_scan --no-llm

`--public-only` still runs listing collectors (Eventbrite city pages, Meetup, …) and skips
authenticated Facebook / Instagram / TikTok. GitHub Actions always uses --public-only.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta

from engine.collect.event_feeds import (
    MCCORMICK_PLACE_NOTE,
    MILWAUKEE_PERMITS_NOTE,
    WINDOW_DAYS,
    collect_dcase_special_events,
    collect_park_district,
    collect_rss_calendars,
    collect_warehouse_cdot,
)
from engine.collect.social import collect_social
from engine.collect.social.config import load_dotenv_secrets
from engine.leads import event_extract, event_store
from engine.leads.event_models import chicago_now, chicago_today


def collect_all(*, public_only: bool) -> tuple[list, list[dict]]:
    notes: list[dict] = [MILWAUKEE_PERMITS_NOTE, MCCORMICK_PLACE_NOTE]
    items = []
    for fn, label in (
        (collect_park_district, "chicago_park_district"),
        (collect_dcase_special_events, "chicago_dcase"),
        (collect_rss_calendars, "tourism_rss"),
        (collect_warehouse_cdot, "chicago_cdot"),
    ):
        try:
            batch = fn()
            items.extend(batch)
            notes.append({"source": label, "status": "ok", "count": len(batch)})
        except Exception as exc:
            notes.append({"source": label, "status": "error", "detail": f"{type(exc).__name__}: {exc}"[:240]})
    try:
        social, social_notes = collect_social(authenticated=not public_only)
        items.extend(social)
        notes.extend(social_notes)
        notes.append(
            {
                "source": "social",
                "status": "ok",
                "count": len(social),
                "authenticated": not public_only,
            }
        )
    except Exception as exc:
        notes.append({"source": "social", "status": "error", "detail": f"{type(exc).__name__}: {exc}"[:240]})
    return items, notes


def build_rows(raw_items, *, use_llm: bool) -> list[dict]:
    today = chicago_today()
    hi = today + timedelta(days=WINDOW_DAYS)
    rows = []
    for item in raw_items:
        if not event_extract.in_fence(item):
            continue
        if item.start:
            try:
                start = date.fromisoformat(item.start[:10])
                if start < today - timedelta(days=1) or start > hi:
                    continue
            except ValueError:
                pass
        extracted = event_extract.enrich(item, use_llm=use_llm)
        row = item.to_dict()
        row.update(extracted)
        row["start"] = extracted.get("date") or item.start
        row["score"] = 0.0
        rows.append(row)
    for row in rows:
        row["score"] = event_extract.score(row, today)
    return event_extract.dedup(rows)


def run(*, public_only: bool, use_llm: bool, require_chicago_hour: bool) -> int:
    load_dotenv_secrets()
    now = chicago_now()
    if require_chicago_hour and now.hour != 7:
        print(f"skip: local Chicago time is {now.isoformat()}, digest runs at 07:00 America/Chicago")
        return 0
    raw, notes = collect_all(public_only=public_only)
    previous = event_store.load_previous()
    rows = build_rows(raw, use_llm=use_llm)
    merged = event_store.merge(previous, rows, now)
    pg = event_store.upsert_postgres(merged)
    merged = event_store.apply_postgres_reviews(merged)
    merged = event_store.apply_local_reviews(merged)
    as_of = now.date().isoformat()
    event_store.write_json(merged, notes=notes, as_of=as_of)
    event_store.write_digest(merged, as_of=as_of)
    by = {}
    for r in merged:
        by[r.get("source") or "?"] = by.get(r.get("source") or "?", 0) + 1
    print(
        f"event-scan {as_of} America/Chicago: {len(raw)} raw -> {len(merged)} stored "
        f"(new {sum(1 for r in merged if r.get('is_new'))}); postgres {pg}; by source {by}"
    )
    for n in notes:
        if n.get("status") not in {"ok"}:
            print(
                f"  {n.get('source')}: {n.get('status')} {n.get('detail') or n.get('records_path') or n.get('note') or ''}"[
                    :220
                ]
            )
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument(
        "--public-only",
        action="store_true",
        help="skip authenticated Facebook/Instagram/TikTok; still run public listings",
    )
    ap.add_argument("--no-llm", action="store_true", help="rule-based extract only")
    ap.add_argument(
        "--require-chicago-hour",
        action="store_true",
        help="no-op unless the local America/Chicago hour is 7 (for dual UTC cron entries)",
    )
    args = ap.parse_args()
    use_llm = not args.no_llm and event_extract.llm_available()
    return run(public_only=args.public_only, use_llm=use_llm, require_chicago_hour=args.require_chicago_hour)


if __name__ == "__main__":
    sys.exit(main())
