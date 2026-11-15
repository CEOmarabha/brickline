"""Polite fetch of a business website's homepage and likely contact pages, with email and phone extraction.

Rules (the founder's compliance requirements, see docs/14-sales-playbook.md):
- robots.txt is honored (urllib.robotparser; Crawl-delay respected up to 10 s); 401/403 on robots.txt means no crawling.
- at most one request per second per host, 10 s timeout, at most 300 KB read per page, identifying User-Agent.
- homepage plus at most 2 contact pages (links to /contact, /contact-us, or link text containing "contact").
- business contact details only: emails on the site's own domain or common free-mail domains, US phone numbers.
  Nothing is guessed from name patterns, and social profiles are never collected.
- results are cached per host in data/raw/web_contacts/<host>.json and reused for 30 days (errors for 3 days).
"""

from __future__ import annotations

import json
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import date
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from urllib.robotparser import RobotFileParser

USER_AGENT = "BricklineResearchBot/0.1 (+contact: founder)"
ROBOT_TOKEN = "BricklineResearchBot"
TIMEOUT = 10
MAX_BYTES = 300 * 1024
MAX_CONTACT_PAGES = 2
MIN_INTERVAL = 1.0
MAX_CRAWL_DELAY = 10.0
CACHE_DAYS = 30
ERROR_CACHE_DAYS = 3
MAX_VALUES = 5
DEADLINE = 25.0  # seconds for one page, including a slow body

SOCIAL_AND_DIRECTORY = (
    "facebook.com", "instagram.com", "linkedin.com", "twitter.com", "x.com", "youtube.com", "tiktok.com",
    "pinterest.com", "yelp.com", "yellowpages.com", "linktr.ee", "angi.com", "angieslist.com", "homeadvisor.com",
    "thumbtack.com", "nextdoor.com", "bbb.org", "mapquest.com", "google.com", "goo.gl", "business.site",
    "wixsite.com", "squarespace.com", "godaddysites.com", "weebly.com", "wordpress.com", "blogspot.com",
)  # fmt: skip
FREE_MAIL = frozenset(
    {
        "gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "aol.com", "icloud.com", "live.com", "msn.com",
        "comcast.net", "sbcglobal.net", "att.net", "ameritech.net", "me.com", "mac.com", "protonmail.com",
    }
)  # fmt: skip
KNOWN_TLDS = frozenset(
    "com net org us biz info co io edu gov pro me tv cc xyz online site shop store tech services solutions group "
    "company construction contractors builders roofing plumbing electric build chicago city contractor homes "
    "design studio works ca uk".split()
)  # fmt: skip
BAD_EMAIL_DOMAINS = (
    "example.com", "example.org", "domain.com", "yourdomain.com", "email.com", "test.com", "sentry.io",
    "sentry-next.wixpress.com", "wixpress.com", "wix.com", "godaddy.com", "squarespace.com", "schema.org",
    "w3.org", "cloudflare.com", "shopify.com", "wordpress.com", "jquery.com", "mysite.com", "company.com",
)  # fmt: skip
BAD_LOCAL = re.compile(r"^(?:no-?reply|do-?not-?reply|donotreply|mailer-daemon|postmaster|webmaster|abuse|"
                       r"your-?(?:name|email)|name|email|user(?:name)?|first(?:name)?\.?last(?:name)?|sentry|"
                       r"privacy|unsubscribe|[0-9a-f]{24,})$", re.I)  # fmt: skip
IMAGE_EXT = re.compile(r"\.(?:png|jpe?g|gif|svg|webp|ico|bmp|css|js|woff2?|ttf|pdf)$", re.I)
EMAIL_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._%+\-]{0,63}@[A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)*\.[A-Za-z]{2,}")
PHONE_RE = re.compile(
    r"(?<![\d.\-])(?:\+?1[\s.\-]?)?(?:\(([2-9]\d{2})\)|([2-9]\d{2}))[\s.\-]*([2-9]\d{2})[\s.\-]?(\d{4})(?!\d)"
)


def host_of(url: str) -> str:
    return (urllib.parse.urlsplit(url).hostname or "").lower()


def base_host(host: str) -> str:
    return host[4:] if host.startswith("www.") else host


def is_social_or_directory(url: str) -> bool:
    h = base_host(host_of(url))
    return any(h == d or h.endswith("." + d) for d in SOCIAL_AND_DIRECTORY)


def clean_website(url: str | None) -> str | None:
    """http(s) origin-level URL for a place website, or None for social/directory pages and junk."""
    if not url:
        return None
    url = url.strip()
    if not re.match(r"^https?://", url, re.I):
        url = "http://" + url
    parts = urllib.parse.urlsplit(url)
    if not parts.hostname or "." not in parts.hostname or is_social_or_directory(url):
        return None
    return f"{parts.scheme.lower()}://{parts.netloc.lower()}{parts.path.rstrip('/') or ''}"


def format_phone(area: str, exchange: str, line: str) -> str:
    return f"({area}) {exchange}-{line}"


def normalize_us_phone(raw: str) -> str | None:
    """'+13125550123', '312.555.0123', '(312) 555-0123' -> '(312) 555-0123'; None if not a valid US number."""
    digits = re.sub(r"\D", "", raw)
    if len(digits) == 11 and digits[0] == "1":
        digits = digits[1:]
    if len(digits) != 10 or digits[0] in "01" or digits[3] in "01":
        return None
    if len(set(digits)) <= 2 or digits[3:6] == "555" and digits[6:8] == "01":
        return None
    return format_phone(digits[:3], digits[3:6], digits[6:])


class _Page(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[tuple[str, str]] = []
        self.text: list[str] = []
        self.mailto: list[str] = []
        self.tel: list[str] = []
        self._skip = 0
        self._href: str | None = None
        self._anchor_text: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "template"):
            self._skip += 1
        elif tag == "a":
            href = dict(attrs).get("href") or ""
            self._href, self._anchor_text = href.strip(), []
            low = href.lower()
            if low.startswith("mailto:"):
                self.mailto.append(unescape(urllib.parse.unquote(href[7:])).split("?")[0].strip())
            elif low.startswith("tel:"):
                self.tel.append(urllib.parse.unquote(href[4:]).strip())

    def handle_endtag(self, tag):
        if tag in ("script", "style", "template") and self._skip:
            self._skip -= 1
        elif tag == "a" and self._href is not None:
            self.links.append((self._href, " ".join("".join(self._anchor_text).split())))
            self._href = None

    def handle_data(self, data):
        if self._skip:
            return
        self.text.append(data)
        if self._href is not None:
            self._anchor_text.append(data)


def _trim_tld(email: str) -> str | None:
    local, _, domain = email.rpartition("@")
    labels = domain.lower().split(".")
    tld = labels[-1]
    if tld not in KNOWN_TLDS:
        tld = next((tld[:k] for k in range(len(tld) - 1, 1, -1) if tld[:k] in KNOWN_TLDS), "")
        if not tld:
            return None
    return f"{local.lower()}@{'.'.join([*labels[:-1], tld])}"


def email_ok(email: str, site_host: str) -> bool:
    local, _, domain = email.partition("@")
    if IMAGE_EXT.search(email) or BAD_LOCAL.match(local) or re.search(r"\d+x\.\w+$|@\d+x", email):
        return False
    if any(domain == d or domain.endswith("." + d) for d in BAD_EMAIL_DOMAINS):
        return False
    base = base_host(site_host)
    return domain == base or domain.endswith("." + base) or base.endswith("." + domain) or domain in FREE_MAIL


def extract(html: str, page_url: str, site_host: str) -> dict:
    """Emails, phones and contact-page link candidates from one HTML page."""
    parser = _Page()
    try:
        parser.feed(html)
        parser.close()
    except Exception:  # malformed markup: use whatever was parsed  # noqa: BLE001
        pass
    text = " ".join(parser.text)
    emails: list[str] = []
    for raw in [*parser.mailto, *EMAIL_RE.findall(text)]:
        for part in re.split(r"[;,\s]+", raw):
            part = part.strip(".,;:()<>[]\"'")
            e = _trim_tld(part) if EMAIL_RE.fullmatch(part) else None
            if e and email_ok(e, site_host) and e not in emails:
                emails.append(e)
    phones: list[str] = []
    for raw in parser.tel:
        p = normalize_us_phone(raw)
        if p and p not in phones:
            phones.append(p)
    for m in PHONE_RE.finditer(text):
        if not re.search(r"[()\s.\-]", m.group(0).strip()):
            continue
        p = normalize_us_phone("".join(g for g in m.groups() if g))
        if p and p not in phones:
            phones.append(p)
    links: list[tuple[int, str]] = []
    for href, label in parser.links:
        if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        url = urllib.parse.urljoin(page_url, href).split("#")[0]
        parts = urllib.parse.urlsplit(url)
        if parts.scheme not in ("http", "https") or base_host((parts.hostname or "").lower()) != base_host(
            site_host
        ):
            continue
        if IMAGE_EXT.search(parts.path):
            continue
        path = parts.path.lower().rstrip("/")
        if re.search(r"/contact(?:-?us)?$", path):
            links.append((0, url))
        elif "contact" in path:
            links.append((1, url))
        elif "contact" in label.lower():
            links.append((2, url))
    return {"emails": emails, "phones": phones, "links": links}


@dataclass
class _Fetched:
    status: int
    url: str
    body: str = ""
    error: str = ""


@dataclass
class _Host:
    host: str
    last: float = 0.0
    delay: float = MIN_INTERVAL
    requests: int = field(default=0)

    def wait(self) -> None:
        gap = self.last + self.delay - time.monotonic()
        if gap > 0:
            time.sleep(gap)
        self.last = time.monotonic()
        self.requests += 1


def _get(url: str, throttle: _Host, text_only: bool = True) -> _Fetched:
    throttle.wait()
    req = urllib.request.Request(
        url, headers={"User-Agent": USER_AGENT, "Accept": "text/html,text/plain;q=0.9"}
    )
    start = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            final = resp.geturl()
            ctype = (resp.headers.get("Content-Type") or "").lower()
            if text_only and ctype and "html" not in ctype and "text" not in ctype and "xml" not in ctype:
                return _Fetched(resp.status, final, error="not html")
            chunks, size = [], 0
            while size <= MAX_BYTES and time.monotonic() - start < DEADLINE:
                chunk = resp.read(16384)
                if not chunk:
                    break
                chunks.append(chunk)
                size += len(chunk)
            data = b"".join(chunks)[:MAX_BYTES]
            charset = resp.headers.get_content_charset() or "utf-8"
            return _Fetched(resp.status, final, data.decode(charset, "replace"))
    except urllib.error.HTTPError as exc:
        return _Fetched(exc.code, url, error=f"http {exc.code}")
    except (urllib.error.URLError, TimeoutError, OSError, ValueError, UnicodeError) as exc:
        return _Fetched(0, url, error=type(exc).__name__)


def crawl(site_url: str, today: date) -> dict:
    """Fetch robots.txt, the homepage and up to 2 contact pages of one site. Always returns a cache record."""
    parts = urllib.parse.urlsplit(site_url)
    origin = f"{parts.scheme}://{parts.netloc}"
    host = (parts.hostname or "").lower()
    rec: dict = {
        "host": host, "origin": origin, "fetchedAt": today.isoformat(), "status": "ok", "pages": [],
        "emails": [], "phones": [],
    }  # fmt: skip
    throttle = _Host(host)

    robots = _get(f"{origin}/robots.txt", throttle, text_only=False)
    rp = RobotFileParser()
    if robots.status in (401, 403):
        rec["status"] = "robots_blocked"
        return rec
    if robots.status == 200 and not robots.error:
        rp.parse(robots.body.splitlines())
        delay = rp.crawl_delay(ROBOT_TOKEN)
        if delay:
            throttle.delay = max(MIN_INTERVAL, min(float(delay), MAX_CRAWL_DELAY))
    elif robots.status == 0 or robots.status >= 500:
        rec.update(status="error", error=f"robots.txt {robots.error or robots.status}")
        return rec
    else:
        rp.parse([])

    def fetch_page(url: str) -> _Fetched | None:
        if not rp.can_fetch(ROBOT_TOKEN, url):
            rec["pages"].append({"url": url, "result": "robots_disallowed"})
            return None
        got = _get(url, throttle)
        final_host = base_host(host_of(got.url))
        ok = got.status == 200 and not got.error and final_host == base_host(host)
        result = (
            "ok"
            if ok
            else (
                "offsite_redirect"
                if got.status == 200 and not got.error
                else got.error or f"http {got.status}"
            )
        )
        rec["pages"].append({"url": got.url if ok else url, "result": result})
        return got if ok else None

    def absorb(got: _Fetched, url: str) -> list[tuple[int, str]]:
        found = extract(got.body, got.url, host)
        for e in found["emails"]:
            if all(x["value"] != e for x in rec["emails"]):
                rec["emails"].append({"value": e, "url": url})
        for p in found["phones"]:
            if all(x["value"] != p for x in rec["phones"]):
                rec["phones"].append({"value": p, "url": url})
        return found["links"]

    home_url = origin + "/"
    home = fetch_page(home_url)
    if home is None:
        blocked = rec["pages"] and rec["pages"][0]["result"] == "robots_disallowed"
        rec["status"] = "robots_blocked" if blocked else "error"
        if not blocked:
            rec["error"] = rec["pages"][0]["result"] if rec["pages"] else "no response"
        return rec
    links = absorb(home, home.url)
    candidates: list[str] = []
    for _, url in sorted(links, key=lambda x: x[0]):
        if url.rstrip("/") != home_url.rstrip("/") and url not in candidates:
            candidates.append(url)
    if not candidates:
        candidates = [f"{origin}/contact", f"{origin}/contact-us"]
    for url in candidates[:MAX_CONTACT_PAGES]:
        got = fetch_page(url)
        if got is not None:
            absorb(got, got.url)
    rec["emails"] = rec["emails"][:MAX_VALUES]
    rec["phones"] = rec["phones"][:MAX_VALUES]
    return rec


def _cache_path(cache_dir: Path, host: str) -> Path:
    return cache_dir / (re.sub(r"[^a-z0-9.\-]", "_", host) + ".json")


def _fresh(rec: dict, today: date) -> bool:
    age = (today - date.fromisoformat(rec["fetchedAt"])).days
    return age < (ERROR_CACHE_DAYS if rec["status"] == "error" else CACHE_DAYS)


def load_cached(cache_dir: Path, site_url: str, today: date) -> dict | None:
    path = _cache_path(cache_dir, host_of(site_url))
    if not path.exists():
        return None
    try:
        rec = json.loads(path.read_text())
    except (OSError, ValueError):
        return None
    return rec if _fresh(rec, today) else None


def crawl_sites(
    site_urls: list[str],
    cache_dir: Path,
    today: date,
    workers: int = 16,
    refresh: bool = False,
    limit: int | None = None,
    log=print,
) -> tuple[dict[str, dict], int]:
    """(records by host, number fetched now): only sites without a fresh cache entry are crawled (at most `limit`)."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    by_host: dict[str, str] = {}
    for url in sorted(site_urls):
        by_host.setdefault(host_of(url), url)
    out: dict[str, dict] = {}
    todo: list[str] = []
    for host, url in by_host.items():
        rec = None if refresh else load_cached(cache_dir, url, today)
        if rec is not None:
            out[host] = rec
        else:
            todo.append(url)
    if limit is not None:
        todo = todo[:limit]
    log(f"  web contacts: {len(out)} cached, {len(todo)} to fetch")
    lock = threading.Lock()
    done = 0

    def work(url: str) -> None:
        nonlocal done
        rec = crawl(url, today)
        path = _cache_path(cache_dir, rec["host"])
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(rec, indent=1, sort_keys=True) + "\n")
        tmp.replace(path)
        with lock:
            out[rec["host"]] = rec
            done += 1
            if done % 100 == 0:
                log(f"    fetched {done}/{len(todo)}")

    with ThreadPoolExecutor(max_workers=workers) as pool:
        list(pool.map(work, todo))
    for host in by_host:
        if host not in out:
            stale = _cache_path(cache_dir, host)
            if stale.exists():
                out[host] = json.loads(stale.read_text())
    return out, len(todo)
