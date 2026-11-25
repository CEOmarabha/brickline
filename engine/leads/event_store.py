"""Incremental event-lead store: JSON snapshot plus optional Postgres upsert."""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from engine.leads.event_models import REVIEW_STATUSES, chicago_now, strip_personal_contacts

JSON_OUT = Path("web/data/event-leads.json")
DIGEST_OUT = Path("web/data/event-digest.json")
STATE_OUT = Path("data/event-scan-state.json")
REVIEWS_OUT = Path("data/event-lead-reviews.json")
MAX_SHIPPED = 600


def load_previous(path: Path = JSON_OUT) -> dict[str, dict]:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    items = data.get("items") if isinstance(data, dict) else None
    if not isinstance(items, list):
        return {}
    return {r["item_hash"]: r for r in items if isinstance(r, dict) and r.get("item_hash")}


def merge(previous: dict[str, dict], incoming: list[dict], now: datetime | None = None) -> list[dict]:
    """Stable item_hash; first_seen/last_seen; content_hash change detection; keep review_status."""
    now = now or chicago_now()
    stamp = now.isoformat()
    out: dict[str, dict] = dict(previous)
    for row in incoming:
        key = row["item_hash"]
        old = out.get(key)
        if old is None:
            row = dict(row)
            row["first_seen"] = stamp
            row["last_seen"] = stamp
            row["changed_at"] = None
            row["review_status"] = "new"
            row["is_new"] = True
            out[key] = row
            continue
        changed = old.get("content_hash") != row.get("content_hash")
        merged = dict(old)
        merged.update(row)
        merged["first_seen"] = old.get("first_seen") or stamp
        merged["last_seen"] = stamp
        merged["changed_at"] = stamp if changed else old.get("changed_at")
        status = old.get("review_status") or "new"
        if status not in REVIEW_STATUSES:
            status = "new"
        merged["review_status"] = status
        merged["is_new"] = False
        merged["changed"] = changed
        out[key] = merged
    return sorted(
        out.values(),
        key=lambda r: (-float(r.get("score") or 0), r.get("start") or "9999", r.get("item_hash") or ""),
    )


def sanitize_for_ship(row: dict) -> dict:
    """Public snapshot: no personal phones/emails, no raw cookie-adjacent extras."""
    skip = {"raw_html", "cookie", "cookies", "storage_state"}
    extra = {k: v for k, v in (row.get("extra") or {}).items() if k not in skip}
    shipped = {k: v for k, v in row.items() if k not in {"raw", "raw_html", "cookie", "cookies"}}
    shipped["extra"] = extra
    for field in ("title", "text", "event_name", "evidence_quote", "host_org", "venue"):
        if isinstance(shipped.get(field), str):
            shipped[field] = strip_personal_contacts(shipped[field])
    return shipped


def write_json(items: list[dict], *, notes: list[dict], as_of: str, path: Path = JSON_OUT) -> Path:
    shipped = [sanitize_for_ship(r) for r in items[:MAX_SHIPPED]]
    payload = {
        "asOf": as_of,
        "generatedAt": chicago_now().isoformat(),
        "counts": _counts(items),
        "notes": notes,
        "items": shipped,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    STATE_OUT.parent.mkdir(parents=True, exist_ok=True)
    STATE_OUT.write_text(
        json.dumps({"asOf": as_of, "items": items}, ensure_ascii=False, default=str) + "\n",
        encoding="utf-8",
    )
    return path


def write_digest(items: list[dict], *, as_of: str, path: Path = DIGEST_OUT, limit: int = 40) -> Path:
    newish = [r for r in items if r.get("is_new") or r.get("changed") or (r.get("review_status") == "new")]
    top = sorted(newish, key=lambda r: (-float(r.get("score") or 0), r.get("item_hash") or ""))[:limit]
    payload = {
        "asOf": as_of,
        "timezone": "America/Chicago",
        "title": f"Event leads digest for {as_of}",
        "counts": _counts(items),
        "top": [sanitize_for_ship(r) for r in top],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def reviews_path() -> Path:
    override = (os.environ.get("EVENT_LEAD_REVIEWS_PATH") or "").strip()
    if override:
        return Path(override).expanduser()
    return REVIEWS_OUT


def apply_postgres_reviews(items: list[dict]) -> list[dict]:
    """Overlay review_status from Postgres so UI changes survive the next scan."""
    return _apply_reviews(items, fetch_postgres_reviews())


def apply_local_reviews(items: list[dict]) -> list[dict]:
    """Overlay review_status from gitignored JSON when DATABASE_URL is unset (no Postgres)."""
    if (os.environ.get("DATABASE_URL") or "").strip():
        return items
    return _apply_reviews(items, fetch_local_reviews())


def _apply_reviews(items: list[dict], reviews: dict[str, str]) -> list[dict]:
    if not reviews:
        return items
    out = []
    for row in items:
        status = reviews.get(row.get("item_hash"))
        if status in REVIEW_STATUSES:
            row = dict(row)
            row["review_status"] = status
        out.append(row)
    return out


def fetch_local_reviews() -> dict[str, str]:
    path = reviews_path()
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(data, dict):
        return {}
    blob = data.get("reviews") if isinstance(data.get("reviews"), dict) else data
    return {str(k): v for k, v in blob.items() if k != "updatedAt" and v in REVIEW_STATUSES}


def write_local_review(item_hash: str, status: str) -> Path:
    """Persist one review status to gitignored JSON. Used by tests; the UI writes the same file."""
    if status not in REVIEW_STATUSES:
        raise ValueError(f"unknown review status: {status}")
    path = reviews_path()
    reviews = fetch_local_reviews()
    reviews[item_hash] = status
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"updatedAt": chicago_now().isoformat(), "reviews": reviews}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def fetch_postgres_reviews() -> dict[str, str]:
    url = (os.environ.get("DATABASE_URL") or "").strip()
    if not url:
        return {}
    try:
        import psycopg
    except ImportError:
        return {}
    try:
        with psycopg.connect(url) as conn:
            with conn.cursor() as cur:
                cur.execute("select item_hash, review_status from event_lead")
                return {h: s for h, s in cur.fetchall() if s in REVIEW_STATUSES}
    except Exception:
        return {}


def upsert_postgres(items: list[dict]) -> str:
    """Insert/update event_lead rows when DATABASE_URL is set. Returns a short status."""
    url = (os.environ.get("DATABASE_URL") or "").strip()
    if not url:
        return "skipped (no DATABASE_URL)"
    try:
        import psycopg
    except ImportError:
        return "skipped (psycopg not installed; web/scripts/upsert-event-leads.mjs can load the JSON)"
    sql = """
        INSERT INTO event_lead (
            item_hash, source, source_url, title, start_date, venue, city, region,
            status, host_org, score, content_hash, raw_json, first_seen, last_seen, changed_at
        ) VALUES (
            %(item_hash)s, %(source)s, %(source_url)s, %(title)s, %(start_date)s, %(venue)s,
            %(city)s, %(region)s, %(status)s, %(host_org)s, %(score)s, %(content_hash)s,
            %(raw_json)s::jsonb, %(first_seen)s::timestamptz, %(last_seen)s::timestamptz,
            %(changed_at)s::timestamptz
        )
        ON CONFLICT (item_hash) DO UPDATE SET
            source_url = EXCLUDED.source_url,
            title = EXCLUDED.title,
            start_date = EXCLUDED.start_date,
            venue = EXCLUDED.venue,
            city = EXCLUDED.city,
            region = EXCLUDED.region,
            status = EXCLUDED.status,
            host_org = EXCLUDED.host_org,
            score = EXCLUDED.score,
            content_hash = EXCLUDED.content_hash,
            raw_json = EXCLUDED.raw_json,
            last_seen = EXCLUDED.last_seen,
            changed_at = COALESCE(EXCLUDED.changed_at, event_lead.changed_at)
    """
    rows = []
    for r in items:
        rows.append(
            {
                "item_hash": r["item_hash"],
                "source": r.get("source"),
                "source_url": r.get("source_url"),
                "title": r.get("event_name") or r.get("title"),
                "start_date": (r.get("start") or r.get("date") or None),
                "venue": r.get("venue"),
                "city": r.get("city"),
                "region": r.get("region"),
                "status": r.get("status"),
                "host_org": r.get("host_org"),
                "score": r.get("score"),
                "content_hash": r.get("content_hash"),
                "raw_json": json.dumps(sanitize_for_ship(r), default=str),
                "first_seen": r.get("first_seen"),
                "last_seen": r.get("last_seen"),
                "changed_at": r.get("changed_at"),
            }
        )
    with psycopg.connect(url) as conn:
        with conn.cursor() as cur:
            cur.executemany(sql, rows)
        conn.commit()
    return f"upserted {len(rows)}"


def _counts(items: list[dict]) -> dict[str, Any]:
    by_source: dict[str, int] = {}
    by_region: dict[str, int] = {}
    for r in items:
        by_source[r.get("source") or "unknown"] = by_source.get(r.get("source") or "unknown", 0) + 1
        if r.get("region"):
            by_region[r["region"]] = by_region.get(r["region"], 0) + 1
    return {
        "total": len(items),
        "new": sum(1 for r in items if r.get("is_new")),
        "changed": sum(1 for r in items if r.get("changed")),
        "bySource": dict(sorted(by_source.items(), key=lambda kv: (-kv[1], kv[0]))),
        "byRegion": by_region,
    }
