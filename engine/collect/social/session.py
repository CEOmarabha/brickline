"""Load Playwright storage_state or cookie JSON exported from the team's own browser.

Never logs cookie values. A missing or expired session is a skip, not a crash.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from engine.collect.social.config import env, env_path, secrets_dir

Platform = Literal["facebook", "instagram", "tiktok"]
COOKIE_ENV = {"facebook": "FB_COOKIE", "instagram": "IG_COOKIE", "tiktok": "TIKTOK_COOKIE"}
STORAGE_ENV = {
    "facebook": "FB_STORAGE_STATE",
    "instagram": "IG_STORAGE_STATE",
    "tiktok": "TIKTOK_STORAGE_STATE",
}
COOKIES_FILE_ENV = {
    "facebook": "FB_COOKIES_FILE",
    "instagram": "IG_COOKIES_FILE",
    "tiktok": "TIKTOK_COOKIES_FILE",
}
DEFAULT_DOMAIN = {
    "facebook": ".facebook.com",
    "instagram": ".instagram.com",
    "tiktok": ".tiktok.com",
}
TEMP_STATE_DIR = Path("data/raw/playwright_state")

LOGIN_MARKERS = (
    "log in",
    "login",
    "sign in",
    "checkpoint",
    "suspicious login",
    "verify it's you",
    "verify its you",
    "enter the code",
    "use your password",
)


class SessionExpired(RuntimeError):
    """The stored session is no longer accepted by the site."""


def storage_state_path(platform: Platform) -> Path | None:
    """Playwright storage_state JSON: {cookies, origins}."""
    if path := env_path(STORAGE_ENV[platform]):
        return path
    candidate = secrets_dir() / f"{platform}.storage.json"
    return candidate if candidate.is_file() else None


def cookies_path(platform: Platform) -> Path | None:
    if path := env_path(COOKIES_FILE_ENV[platform]):
        return path
    for name in (f"{platform}.cookies.json", f"{platform}.cookies.txt"):
        candidate = secrets_dir() / name
        if candidate.is_file():
            return candidate
    return None


def session_configured(platform: Platform) -> bool:
    return bool(storage_state_path(platform) or cookies_path(platform) or env(COOKIE_ENV[platform]))


def playwright_storage_path(platform: Platform) -> Path | None:
    """Path Playwright can load as storage_state, including a temp file built from exported cookies."""
    if path := storage_state_path(platform):
        return path
    cookies = _cookie_objects(platform)
    if not cookies:
        return None
    TEMP_STATE_DIR.mkdir(parents=True, exist_ok=True)
    dest = TEMP_STATE_DIR / f"{platform}.storage.json"
    dest.write_text(
        json.dumps({"cookies": cookies, "origins": []}, ensure_ascii=False),
        encoding="utf-8",
    )
    return dest


def load_cookie_header(platform: Platform) -> str | None:
    """Cookie header string, or None when no session file is configured."""
    raw = env(COOKIE_ENV[platform])
    if raw:
        return raw
    path = cookies_path(platform)
    if path is None:
        state = storage_state_path(platform)
        if state is None:
            return None
        return _header_from_storage(state)
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".txt" or text.lstrip().startswith("#"):
        return _header_from_netscape(text)
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return _header_from_netscape(text)
    if isinstance(data, dict) and "cookies" in data:
        return _header_from_cookies(data["cookies"])
    if isinstance(data, list):
        return _header_from_cookies(data)
    return None


def looks_logged_out(html: str) -> bool:
    low = html.lower()
    if "c_user=" in html or '"viewerID"' in html or '"viewer_id"' in html:
        return False
    if "sessionid" in html.lower() and "instagram.com" in low and "log in" not in low:
        return False
    return any(m in low for m in LOGIN_MARKERS) and "logout" not in low and "log out" not in low


def _cookie_objects(platform: Platform) -> list[dict]:
    """Normalize env/file cookies into Playwright cookie dicts. Never logs values."""
    domain = DEFAULT_DOMAIN[platform]
    raw = env(COOKIE_ENV[platform])
    if raw:
        return [_cookie(name, value, domain) for name, value in _pairs_from_header(raw)]
    path = cookies_path(platform)
    if path is None:
        return []
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".txt" or text.lstrip().startswith("# Netscape"):
        return _cookies_from_netscape(text, domain)
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return _cookies_from_netscape(text, domain)
    if isinstance(data, dict) and isinstance(data.get("cookies"), list):
        return [_normalize_cookie(c, domain) for c in data["cookies"] if isinstance(c, dict)]
    if isinstance(data, list):
        return [_normalize_cookie(c, domain) for c in data if isinstance(c, dict)]
    return []


def _pairs_from_header(header: str) -> list[tuple[str, str]]:
    pairs = []
    for part in header.split(";"):
        if "=" not in part:
            continue
        name, _, value = part.strip().partition("=")
        if name:
            pairs.append((name.strip(), value.strip()))
    return pairs


def _cookie(name: str, value: str, domain: str, **extra: object) -> dict:
    cookie = {
        "name": name,
        "value": value,
        "domain": extra.get("domain") or domain,
        "path": extra.get("path") or "/",
        "expires": extra.get("expires", -1),
        "httpOnly": bool(extra.get("httpOnly", False)),
        "secure": bool(extra.get("secure", True)),
        "sameSite": extra.get("sameSite") or "Lax",
    }
    return cookie


def _normalize_cookie(raw: dict, domain: str) -> dict:
    expires = raw.get("expires")
    if expires is None:
        expires = raw.get("expirationDate", -1)
    same = raw.get("sameSite") or raw.get("same_site") or "Lax"
    if isinstance(same, str):
        folded = same.lower()
        if folded in {"no_restriction", "none"}:
            same = "None"
        elif folded in {"lax", "strict"}:
            same = folded.capitalize()
        else:
            same = "Lax"
    return _cookie(
        str(raw.get("name") or ""),
        str(raw.get("value") or ""),
        domain,
        domain=raw.get("domain") or domain,
        path=raw.get("path") or "/",
        expires=expires if expires is not None else -1,
        httpOnly=raw.get("httpOnly") or raw.get("http_only") or False,
        secure=raw.get("secure", True),
        sameSite=same,
    )


def _cookies_from_netscape(text: str, domain: str) -> list[dict]:
    out = []
    for line in text.splitlines():
        if not line or line.startswith("#"):
            continue
        cols = line.split("\t")
        if len(cols) < 7:
            continue
        out.append(
            _cookie(
                cols[5],
                cols[6],
                domain,
                domain=cols[0] or domain,
                path=cols[2] or "/",
                expires=float(cols[4]) if cols[4].replace(".", "", 1).isdigit() else -1,
                httpOnly=cols[1].upper() == "TRUE",
                secure=cols[3].upper() == "TRUE",
            )
        )
    return out


def _header_from_storage(path: Path) -> str | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return _header_from_cookies(data.get("cookies") or [])


def _header_from_cookies(cookies: list) -> str | None:
    parts = []
    for c in cookies:
        if not isinstance(c, dict):
            continue
        name, value = c.get("name"), c.get("value")
        if name and value is not None:
            parts.append(f"{name}={value}")
    return "; ".join(parts) if parts else None


def _header_from_netscape(text: str) -> str | None:
    parts = []
    for line in text.splitlines():
        if not line or line.startswith("#"):
            continue
        cols = line.split("\t")
        if len(cols) >= 7:
            parts.append(f"{cols[5]}={cols[6]}")
    return "; ".join(parts) if parts else None
