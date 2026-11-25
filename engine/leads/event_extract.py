"""Extract, geo-fence, fuzzy-dedup and score event leads.

Optional LLM JSON extraction (Anthropic, Gemini's OpenAI-compatible endpoint, or a generic
OpenAI-compatible server such as Ollama / Groq / OpenRouter). The model is forbidden from
inventing contacts; any phone/email it returns is dropped. Rule-based extraction always runs
so the pipeline works at $0 without a key.
"""

from __future__ import annotations

import json
import re
import urllib.request
from datetime import date
from typing import Any

from engine.collect.social.config import REGIONS, env
from engine.enrich.names import normalize, token_set_ratio
from engine.leads.event_models import (
    PERSONAL_EMAIL_RE,
    PERSONAL_PHONE_RE,
    VENDOR_NEEDS,
    RawEvent,
    chicago_today,
    strip_personal_contacts,
)

VENDOR_HINTS = {
    "dj": r"\bdjs?\b|disc jockey|looking for a dj|need a dj",
    "caterer": r"cater(?:er|ing)|need food|looking for a cater",
    "venue": r"\bvenue\b|banquet hall|looking for a (?:place|space|hall)",
    "tent": r"\btents?\b|canopy|party tent",
    "tables": r"tables and chairs|table rental|chair rental",
    "photo": r"photographer|photography",
    "video": r"videographer|videography",
    "florist": r"florist|floral|bouquet",
    "decor": r"decorat(?:e|or|ion)|balloon",
    "lighting": r"uplight|string light|lighting",
    "bartender": r"bartender|bar service|open bar",
    "planner": r"event planner|need a planner|coordinator",
    "bounce_house": r"bounce house|inflatable|moonwalk",
    "photo_booth": r"photo booth",
    "security": r"\bsecurity\b|off-duty",
    "transport": r"party bus|limo|shuttle",
    "makeup": r"makeup artist|mua\b",
    "cake": r"\bcake\b|bakery",
    "officiant": r"officiant|justice of the peace",
}

SIZE_RE = re.compile(
    r"(\d{2,4})\s*(?:guests?|people|pax|attendees|person)\b",
    re.I,
)
INTENT_RE = re.compile(
    r"looking for|need a |need an |anyone know.*(dj|cater|venue|photo)|quien (?:sabe|tiene)",
    re.I,
)

GEMINI_OPENAI_BASE = "https://generativelanguage.googleapis.com/v1beta/openai"
LLM_SYSTEM = (
    "Extract a public event lead. Reply with JSON only, no markdown. "
    "Never invent a phone, email, handle or contact. If a contact is not in the text, omit it. "
    "If the text is not an event or a request for event vendors, set confidence to 0."
)
LLM_USER_PREFIX = (
    "Schema: {event_name, date (YYYY-MM-DD or null), venue, city, "
    "region (chicagoland|milwaukee|nw_indiana|null), host_org, est_size (int or null), "
    "vendor_needs (array of short tags), evidence_quote (short substring copied from the text), "
    "confidence (0-1)}. Text:\n"
)


def geo_region(text: str, city: str | None = None) -> str | None:
    blob = f"{city or ''} {text}".upper()
    for region, places in REGIONS.items():
        for place in places:
            if place.upper() in blob:
                return region
    if re.search(r",\s*IL\b|\bILLINOIS\b|\b606\d{2}\b", blob):
        return "chicagoland"
    if re.search(r",\s*WI\b|\bWISCONSIN\b|\b532\d{2}\b", blob):
        return "milwaukee"
    if re.search(r",\s*IN\b|\bINDIANA\b|\b463\d{2}\b|\b464\d{2}\b", blob):
        return "nw_indiana"
    return None


def in_fence(item: RawEvent) -> bool:
    region = item.region or geo_region(item.text + " " + (item.title or ""), item.city)
    if region:
        item.region = region
        return True
    # Permit/calendar sources already tagged; social without a place is dropped.
    return item.source in {
        "chicago_park_district",
        "chicago_dcase",
        "chicago_cdot",
        "choose_chicago",
        "visit_milwaukee",
        "south_shore_cva",
    }


def vendor_needs_of(text: str) -> list[str]:
    found = []
    for key in VENDOR_NEEDS:
        if re.search(VENDOR_HINTS.get(key, rf"\b{key}\b"), text, re.I):
            found.append(key)
    return found


def rule_extract(item: RawEvent) -> dict[str, Any]:
    text = " ".join(x for x in (item.title, item.text, item.venue, item.city) if x)
    size = None
    m = SIZE_RE.search(text)
    if m:
        size = int(m.group(1))
        if size > 5000:
            size = None
    quote = None
    if INTENT_RE.search(text):
        quote = _snippet(text, INTENT_RE.search(text).start())
    needs = vendor_needs_of(text)
    region = item.region or geo_region(text, item.city)
    return {
        "event_name": item.title,
        "date": item.start,
        "venue": item.venue,
        "city": item.city,
        "region": region,
        "host_org": item.host_org,
        "est_size": size,
        "vendor_needs": needs,
        "evidence_quote": quote,
        "confidence": 0.55 if (item.title and item.start) else 0.35,
        "intent": bool(INTENT_RE.search(text) or needs),
    }


def llm_available() -> bool:
    """True when any supported LLM credential is set (Anthropic, Gemini, or OpenAI-compatible)."""
    return bool(
        env("ANTHROPIC_API_KEY") or env("GEMINI_API_KEY") or env("OPENAI_API_KEY") or env("OPENAI_BASE_URL")
    )


def openai_endpoint() -> tuple[str, str, str] | None:
    """Return (base_url, api_key, model) for an OpenAI-compatible chat server, or None.

    Resolution order when Anthropic is not used:
    1. OPENAI_BASE_URL (+ OPENAI_API_KEY + OPENAI_MODEL) — Ollama at
       http://localhost:11434/v1, Groq, OpenRouter, a self-hosted proxy, etc.
    2. GEMINI_API_KEY → https://generativelanguage.googleapis.com/v1beta/openai/
    3. OPENAI_API_KEY alone → https://api.openai.com/v1
    """
    base = env("OPENAI_BASE_URL").rstrip("/")
    key = env("OPENAI_API_KEY")
    model = env("OPENAI_MODEL") or env("LLM_MODEL")
    if base:
        if not key:
            key = "ollama" if "11434" in base else "dummy"
        if not model:
            model = "llama3.2" if "11434" in base else "gpt-4o-mini"
        return base, key, model
    gemini = env("GEMINI_API_KEY")
    if gemini:
        return GEMINI_OPENAI_BASE, gemini, env("GEMINI_MODEL") or "gemini-2.0-flash"
    if key:
        return "https://api.openai.com/v1", key, model or "gpt-4o-mini"
    return None


def llm_extract(item: RawEvent) -> dict[str, Any] | None:
    """Strict JSON via Anthropic or an OpenAI-compatible endpoint. Never keeps invented contacts."""
    parsed = _anthropic_extract(item) or _openai_extract(item)
    return _sanitize_llm(parsed) if parsed else None


def _user_payload(item: RawEvent) -> str:
    return LLM_USER_PREFIX + json.dumps(
        {
            "title": item.title,
            "text": item.text[:2500],
            "venue": item.venue,
            "city": item.city,
            "start": item.start,
            "source_url": item.source_url,
        },
        ensure_ascii=False,
    )


def _anthropic_extract(item: RawEvent) -> dict[str, Any] | None:
    key = env("ANTHROPIC_API_KEY")
    if not key:
        return None
    model = env("ASSISTANT_MODEL") or "claude-sonnet-5-5"
    prompt = {
        "model": model,
        "max_tokens": 600,
        "system": LLM_SYSTEM,
        "messages": [{"role": "user", "content": _user_payload(item)}],
    }
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps(prompt).encode(),
        headers={
            "content-type": "application/json",
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            body = json.loads(resp.read().decode("utf-8", "replace"))
    except Exception:
        return None
    chunks = [
        c.get("text", "")
        for c in body.get("content") or []
        if isinstance(c, dict) and c.get("type") == "text"
    ]
    return _parse_llm_json("\n".join(chunks))


def _openai_extract(item: RawEvent) -> dict[str, Any] | None:
    endpoint = openai_endpoint()
    if not endpoint:
        return None
    base, key, model = endpoint
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": LLM_SYSTEM},
            {"role": "user", "content": _user_payload(item)},
        ],
        "max_tokens": 600,
        "temperature": 0,
    }
    url = f"{base}/chat/completions"
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={
            "content-type": "application/json",
            "authorization": f"Bearer {key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            body = json.loads(resp.read().decode("utf-8", "replace"))
    except Exception:
        return None
    if not isinstance(body, dict):
        return None
    choices = body.get("choices") or []
    if not choices or not isinstance(choices[0], dict):
        return None
    message = choices[0].get("message") or {}
    content = message.get("content") if isinstance(message, dict) else None
    if isinstance(content, list):
        parts = []
        for part in content:
            if isinstance(part, dict):
                parts.append(str(part.get("text") or part.get("content") or ""))
            else:
                parts.append(str(part))
        content = "".join(parts)
    if not isinstance(content, str):
        return None
    return _parse_llm_json(content)


def _parse_llm_json(raw: str) -> dict[str, Any] | None:
    text = raw.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text).strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start < 0 or end <= start:
            return None
        try:
            parsed = json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            return None
    return parsed if isinstance(parsed, dict) else None


def _sanitize_llm(parsed: dict[str, Any]) -> dict[str, Any]:
    parsed = dict(parsed)
    parsed.pop("phone", None)
    parsed.pop("email", None)
    parsed.pop("contacts", None)
    quote = parsed.get("evidence_quote")
    if isinstance(quote, str):
        parsed["evidence_quote"] = strip_personal_contacts(quote)[:280]
    needs = parsed.get("vendor_needs") or []
    parsed["vendor_needs"] = [n for n in needs if n in VENDOR_NEEDS]
    try:
        parsed["confidence"] = max(0.0, min(1.0, float(parsed.get("confidence") or 0)))
    except (TypeError, ValueError):
        parsed["confidence"] = 0.0
    return parsed


def enrich(item: RawEvent, *, use_llm: bool = True) -> dict[str, Any]:
    base = rule_extract(item)
    if use_llm:
        llm = llm_extract(item)
        if llm:
            for key in (
                "event_name",
                "date",
                "venue",
                "city",
                "region",
                "host_org",
                "est_size",
                "evidence_quote",
            ):
                if llm.get(key) not in (None, "", []):
                    base[key] = llm[key]
            if llm.get("vendor_needs"):
                base["vendor_needs"] = sorted(set(base["vendor_needs"]) | set(llm["vendor_needs"]))
            base["confidence"] = max(base["confidence"], llm.get("confidence") or 0)
            base["extractor"] = "llm"
        else:
            base["extractor"] = "rules"
    else:
        base["extractor"] = "rules"
    if PERSONAL_PHONE_RE.search(json.dumps(base)) or PERSONAL_EMAIL_RE.search(json.dumps(base)):
        base["host_org"] = base.get("host_org")
        base["evidence_quote"] = strip_personal_contacts(base.get("evidence_quote") or "")
    base["region"] = base.get("region") or item.region
    return base


def dedup(rows: list[dict], threshold: float = 0.85) -> list[dict]:
    """Keep the highest-scoring row of each fuzzy (name, date, venue) cluster."""
    kept: list[dict] = []
    for row in sorted(rows, key=lambda r: (-float(r.get("score") or 0), r.get("item_hash") or "")):
        name = normalize(row.get("event_name") or row.get("title") or "")
        day = (row.get("start") or row.get("date") or "")[:10]
        venue = normalize(row.get("venue") or "")
        duplicate = False
        for other in kept:
            on = normalize(other.get("event_name") or other.get("title") or "")
            od = (other.get("start") or other.get("date") or "")[:10]
            ov = normalize(other.get("venue") or "")
            if day and od and day != od:
                continue
            same_name = bool(name and on and token_set_ratio(name, on) >= threshold)
            same_venue = (not venue or not ov) or token_set_ratio(venue, ov) >= threshold
            if same_name and same_venue:
                duplicate = True
                other.setdefault("duplicates", []).append(row.get("item_hash"))
                break
        if not duplicate:
            kept.append(row)
    return kept


def score(row: dict, today: date | None = None) -> float:
    """0-100: recency, notice window, size, vendor-need, contactability."""
    today = today or chicago_today()
    recency = 20.0
    first = row.get("first_seen")
    if first:
        try:
            age = (today - date.fromisoformat(str(first)[:10])).days
            recency = max(0.0, 25.0 - age * 1.5)
        except ValueError:
            recency = 15.0
    notice = 8.0
    start = row.get("start") or row.get("date")
    if start:
        try:
            days = (date.fromisoformat(str(start)[:10]) - today).days
            if 14 <= days <= 56:
                notice = 25.0
            elif 7 <= days < 14 or 56 < days <= 90:
                notice = 16.0
            elif 1 <= days < 7:
                notice = 8.0
            elif days > 90:
                notice = 12.0
            else:
                notice = 2.0
        except ValueError:
            notice = 8.0
    size_pts = 0.0
    est = row.get("est_size")
    if isinstance(est, int):
        size_pts = 15.0 if est >= 150 else 10.0 if est >= 50 else 6.0
    needs = row.get("vendor_needs") or []
    need_pts = min(20.0, 6.0 * len(needs) + (8.0 if row.get("intent") else 0.0))
    contact = 0.0
    if row.get("host_org"):
        contact += 10.0
    if row.get("source_url"):
        contact += 5.0
    total = recency + notice + size_pts + need_pts + contact
    return round(min(100.0, total), 2)


def _snippet(text: str, at: int, width: int = 140) -> str:
    lo = max(0, at - 40)
    hi = min(len(text), at + width)
    return strip_personal_contacts(text[lo:hi].strip())
