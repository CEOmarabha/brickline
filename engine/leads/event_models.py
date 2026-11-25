"""Shared shapes for the daily event-lead scanner (collectors, extract, store, digest)."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo

REGIONS = ("chicagoland", "milwaukee", "nw_indiana")
REVIEW_STATUSES = ("new", "approved", "rejected", "contacted")
VENDOR_NEEDS = (
    "dj",
    "caterer",
    "venue",
    "tent",
    "tables",
    "photo",
    "video",
    "florist",
    "decor",
    "lighting",
    "bartender",
    "planner",
    "bounce_house",
    "photo_booth",
    "security",
    "transport",
    "makeup",
    "cake",
    "officiant",
)

# Personal phones/emails never go into shipped JSON (web/data). Postgres may keep them for the private app.
PERSONAL_PHONE_RE = re.compile(
    r"(?<![\d.\-])(?:\+?1[\s.\-]?)?(?:\(([2-9]\d{2})\)|([2-9]\d{2}))[\s.\-]*([2-9]\d{2})[\s.\-]?(\d{4})(?!\d)"
)
PERSONAL_EMAIL_RE = re.compile(
    r"[A-Za-z0-9][A-Za-z0-9._%+\-]{0,63}@[A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)*\.[A-Za-z]{2,}"
)


@dataclass
class RawEvent:
    """One item from a collector, before extract/dedup/score."""

    source: str
    source_url: str
    title: str | None = None
    start: str | None = None
    end: str | None = None
    venue: str | None = None
    city: str | None = None
    region: str | None = None
    text: str = ""
    status: str | None = None
    host_org: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def item_key(self) -> str:
        return "|".join(
            [
                self.source,
                (self.source_url or "").strip().lower(),
                (self.title or "").strip().lower(),
                (self.start or "")[:10],
                (self.venue or "").strip().lower(),
            ]
        )

    def item_hash(self) -> str:
        return hashlib.sha256(self.item_key().encode()).hexdigest()[:32]

    def content_hash(self) -> str:
        payload = {
            "title": self.title,
            "start": self.start,
            "end": self.end,
            "venue": self.venue,
            "city": self.city,
            "status": self.status,
            "host_org": self.host_org,
            "text": self.text,
        }
        blob = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        return hashlib.sha256(blob.encode()).hexdigest()[:32]

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["item_hash"] = self.item_hash()
        d["content_hash"] = self.content_hash()
        return d


def chicago_now() -> datetime:
    return datetime.now(ZoneInfo("America/Chicago"))


def chicago_today() -> date:
    return chicago_now().date()


def iso_day(value: date | datetime | str | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    text = str(value).strip()
    if not text:
        return None
    return text[:10]


def strip_personal_contacts(text: str | None) -> str:
    """Drop phone numbers and emails so shipped files never carry private-person contact details."""
    if not text:
        return ""
    out = PERSONAL_PHONE_RE.sub("[phone withheld]", text)
    return PERSONAL_EMAIL_RE.sub("[email withheld]", out)
