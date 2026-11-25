"""Keywords, regions and env-driven provider settings for social collectors."""

from __future__ import annotations

import json
import os
from pathlib import Path

REGIONS = {
    "chicagoland": (
        "Chicago",
        "Chicagoland",
        "Evanston",
        "Oak Park",
        "Naperville",
        "Aurora",
        "Joliet",
        "Schaumburg",
        "Skokie",
        "Cicero",
        "Waukegan",
        "Elgin",
    ),
    "milwaukee": (
        "Milwaukee",
        "Waukesha",
        "Racine",
        "Kenosha",
        "Brookfield",
        "West Allis",
        "Wauwatosa",
        "Ozaukee",
    ),
    "nw_indiana": (
        "Hammond",
        "Gary",
        "Munster",
        "Highland",
        "Merrillville",
        "Valparaiso",
        "Michigan City",
        "Portage",
        "Crown Point",
        "Northwest Indiana",
        "NW Indiana",
        "NWI",
        "South Shore",
    ),
}

INTENT_QUERIES = (
    "looking for a DJ",
    "need a caterer",
    "need a DJ",
    "venue for",
    "quinceanera",
    "quinceañera",
    "wedding",
    "corporate party",
    "looking for a photographer",
    "need a florist",
    "tent rental",
    "looking for a venue",
)

REDDIT_SUBS = (
    "chicago",
    "milwaukee",
    "indiana",
    "nwi",
    "GaryIN",
    "hammond",
    "naperville",
    "chicagosuburbs",
    "oakpark",
    "wisconsin",
)

DEFAULT_APIFY_ACTORS = {
    "facebook": "apify/facebook-events-scraper",
    "instagram": "apify/instagram-scraper",
    "tiktok": "clockworks/tiktok-scraper",
    "eventbrite": "apify/eventbrite-scraper",
}


def env(name: str, default: str = "") -> str:
    return (os.environ.get(name) or default).strip()


def env_path(name: str) -> Path | None:
    raw = env(name)
    if not raw:
        return None
    path = Path(raw).expanduser()
    return path if path.is_file() else None


def secrets_dir() -> Path:
    override = env("EVENT_SCAN_SECRETS_DIR")
    if override:
        return Path(override).expanduser()
    return Path("secrets")


def load_dotenv_secrets() -> None:
    """Load secrets/event-scanner.env into os.environ without overriding real env vars.

    The file is gitignored. Never print its values.
    """
    path = secrets_dir() / "event-scanner.env"
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def queries_for_region() -> list[tuple[str, str]]:
    """(query, region) pairs combining intent language with a place name."""
    out: list[tuple[str, str]] = []
    for region, places in REGIONS.items():
        place = places[0]
        for intent in INTENT_QUERIES:
            out.append((f"{intent} {place}", region))
    return out


def json_env(name: str) -> dict | list | None:
    raw = env(name)
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None
