"""Chicago City Clerk eLMS: zoning reclassification ordinances (Council map amendments).

The City Council's legislative API (https://api.chicityclerkelms.chicago.gov, Swagger UI at the root, public, no
key) lists every ordinance with an introduction date, a status and, for passed ones, a final action date. Zoning
reclassifications are the earliest public pre-permit trail for large Chicago projects: a title such as
"Zoning Reclassification Map No. 3-G at 1234-1240 W Fullerton Ave - App No. 22123T1" is filed months before any
building permit exists.

Two things about the data shaped this collector (both verified against the API on 2026-11-16):

* Records since 2021 sit in the category "ZONING RECLASSIFICATIONS"; older ones carry one category per map sheet
  ("ZONING RECLASSIFICATIONS | Map No. 7-L"), so a category filter returns only 1,487 matters since 2015. The
  phrase search "Zoning Reclassification Map No" finds both generations; it is combined with a `fileYear` filter so
  every request returns at most 500 rows (the API maximum). Titles are filtered again here.
* The list endpoint carries everything needed (title, introduction date, status, final action date, sponsor,
  committee). The per-matter endpoint adds the action history and attachment names; it costs one request per
  matter, so it is optional (`--details`). The ordinance PDFs are scanned images (no text layer for recent years),
  so from/to districts are only available when the title states them.

Polite: descriptive User-Agent, at most one request per second, retries with backoff, `Retry-After` honoured, the
host's robots.txt checked (it returns 404, i.e. no restrictions). Raw pages are kept in data/raw/clerk/ (gitignored);
list pages are re-fetched on every sync (about 20 requests) and per-matter pages are cached.

    uv run python -m engine.collect.clerk                 # list pages 2012-present
    uv run python -m engine.collect.clerk --details 200   # also fetch up to 200 per-matter pages (cached)
"""

from __future__ import annotations

import argparse
import http.client
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from pathlib import Path

BASE = "https://api.chicityclerkelms.chicago.gov"
UA = "BricklineResearchBot/0.1 (public-records research; +contact: founder)"
RAW = Path("data/raw/clerk")
SEARCH_PHRASE = '"Zoning Reclassification Map No"'
FIRST_YEAR = 2012
PAGE = 500
MIN_INTERVAL = 1.0
TITLE_RE = re.compile(r"^\s*zoning\s+reclassification\s+map\s+no", re.IGNORECASE)


def retry_after(value: str | None) -> float:
    """Seconds named by a Retry-After header (a number or an HTTP date); 0 when absent or unreadable."""
    if not value:
        return 0.0
    try:
        return max(0.0, float(value))
    except ValueError:
        pass
    try:
        return max(0.0, (parsedate_to_datetime(value) - datetime.now(UTC)).total_seconds())
    except (TypeError, ValueError):
        return 0.0


class Fetcher:
    """One request per second, retries with exponential backoff, robots.txt respected."""

    def __init__(self, base: str = BASE, ua: str = UA, min_interval: float = MIN_INTERVAL, log=print):
        self.base, self.ua, self.min_interval, self.log = base, ua, min_interval, log
        self._last = 0.0
        self._robots = urllib.robotparser.RobotFileParser()
        self._robots_loaded = False

    def _wait(self) -> None:
        gap = self.min_interval - (time.monotonic() - self._last)
        if gap > 0:
            time.sleep(gap)
        self._last = time.monotonic()

    def _allowed(self, path: str) -> bool:
        if not self._robots_loaded:
            try:
                self._wait()
                req = urllib.request.Request(self.base + "/robots.txt", headers={"User-Agent": self.ua})
                with urllib.request.urlopen(req, timeout=60) as resp:
                    self._robots.parse(resp.read().decode("utf-8", "replace").splitlines())
            except urllib.error.HTTPError as exc:
                # 404 means no robots.txt: no restrictions. Any other refusal is treated as "do not crawl".
                if exc.code == 404:
                    self._robots.parse([])
                else:
                    self._robots.parse(["User-agent: *", "Disallow: /"])
            self._robots_loaded = True
        return self._robots.can_fetch(self.ua, self.base + path)

    def get_json(self, path: str, params: dict | None = None, attempts: int = 6) -> dict:
        if not self._allowed(path):
            raise RuntimeError(f"robots.txt disallows {path}")
        url = self.base + path + ("?" + urllib.parse.urlencode(params) if params else "")
        for attempt in range(attempts):
            self._wait()
            try:
                req = urllib.request.Request(
                    url, headers={"User-Agent": self.ua, "Accept": "application/json"}
                )
                with urllib.request.urlopen(req, timeout=120) as resp:
                    return json.loads(resp.read())
            except urllib.error.HTTPError as exc:
                if exc.code not in (429, 500, 502, 503, 504) or attempt == attempts - 1:
                    raise
                delay = min(retry_after(exc.headers.get("Retry-After")), 300) or 4 * 2**attempt
            except (OSError, http.client.HTTPException, json.JSONDecodeError):
                if attempt == attempts - 1:
                    raise
                delay = 4 * 2**attempt
            self.log(f"  retry in {delay:.0f}s: {url}")
            time.sleep(delay)
        raise AssertionError("unreachable")


def _write_atomic(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, sort_keys=True))
    tmp.rename(path)


def sync(out_dir: Path = RAW, since_year: int = FIRST_YEAR, details: int = 0, log=print) -> None:
    """Fetch list pages for every fileYear from `since_year` to next year; optionally cache matter details."""
    fx = Fetcher(log=log)
    this_year = datetime.now(UTC).year
    for year in range(since_year, this_year + 2):
        page = 0
        while True:
            body = fx.get_json(
                "/matter",
                {
                    "top": PAGE,
                    "skip": page * PAGE,
                    "sort": "introductionDate asc",
                    "search": SEARCH_PHRASE,
                    "filter": f"fileYear eq {year}",
                },
            )
            _write_atomic(out_dir / "list" / f"list-{year}-{page:02d}.json", body)
            meta = body.get("meta") or {}
            log(f"  clerk {year} page {page}: {len(body.get('data') or [])} of {meta.get('count')}")
            if (page + 1) * PAGE >= (meta.get("count") or 0):
                break
            page += 1
        for stale in (out_dir / "list").glob(f"list-{year}-*.json"):
            if int(stale.stem.rsplit("-", 1)[1]) > page:
                stale.unlink()
    if details:
        fetch_details(fx, out_dir, details, log)


def list_matters(out_dir: Path = RAW) -> list[dict]:
    """All list rows whose title is a zoning reclassification, de-duplicated by matterId, sorted by record number."""
    seen: dict[str, dict] = {}
    for path in sorted((out_dir / "list").glob("list-*.json")):
        for row in json.loads(path.read_text()).get("data") or []:
            if TITLE_RE.match(row.get("title") or ""):
                seen[row["matterId"]] = row
    return sorted(seen.values(), key=lambda r: (r.get("recordNumber") or "", r["matterId"]))


def fetch_details(fx: Fetcher, out_dir: Path, limit: int, log=print) -> None:
    """Cache /matter/{id} (action history, sponsors, attachment names) for the newest matters first."""
    todo = sorted(
        list_matters(out_dir), key=lambda r: (r.get("introductionDate") or "", r["matterId"]), reverse=True
    )
    done = 0
    for row in todo:
        path = out_dir / "matter" / f"{row['matterId']}.json"
        if path.exists():
            cached = json.loads(path.read_text())
            if cached.get("lastPublicationDate") == row.get("lastPublicationDate"):
                continue
        _write_atomic(path, fx.get_json(f"/matter/{row['matterId']}"))
        done += 1
        if done % 50 == 0:
            log(f"  clerk details: {done}")
        if done >= limit:
            break


# Parsing -----------------------------------------------------------------------------------------------------
MAP_RE = re.compile(r"map\s+no\.?\s*([0-9]+\s*-?\s*[A-Z0-9]+)", re.IGNORECASE)
APP_RE = re.compile(r"app(?:lication)?\.?\s*no\.?\s*[:#]?\s*([A-Z0-9\-]+)", re.IGNORECASE)
ADDR_START_RE = re.compile(
    r"(?<![0-9\-])(?:\d{1,5}(?:\s*(?:-|to)\s*\d{1,5})?\s*(?:,\s*|\s+and\s+|\s*&\s*))*"
    r"\d{1,5}(?:\s*(?:-|to)\s*\d{1,5})?\s*(?:NORTH|SOUTH|EAST|WEST|N|S|E|W)\b\.?\s+\S",
    re.IGNORECASE,
)
# Separators between addresses: "and", "&", commas, slashes, semicolons, "amd" (typo for and), "to" before a number,
# "a.k.a." / "also known as" / "commonly known as" (the alias is another address of the same property), parentheses,
# and a missing separator before the next "<number> <direction>" ("... 76th St 1121-1147 E 76th St").
SEGMENT_SPLIT_RE = re.compile(
    r"\s+and\s+|\s+amd\s+|\s*&\s*|\s*[,/;()]\s*|\s+to\s+(?=\d)"
    r"|\s*\b(?:a\.?\s?k\.?\s?a\.?|also\s+known\s+as|commonly\s+known?\s+as|properties\s+with\s+address\s+ranges\s+of)\s+"
    r"|(?<=[A-Za-z])\s+(?=\d{1,5}(?:-\d{1,5})?\s+[NSEW]\b)",
    re.IGNORECASE,
)
BARE_NUMBER_RE = re.compile(r"^(\d{1,5})(?:\s*(?:-|to)\s*(\d{1,5}))?$")
SEGMENT_RE = re.compile(
    r"^(\d{1,5})(?:\s*(?:-|to)\s*(\d{1,5}))?\s*(NORTH|SOUTH|EAST|WEST|N|S|E|W)\b\.?\s+(.+)$", re.IGNORECASE
)
DIRECTIONS = {"NORTH": "N", "SOUTH": "S", "EAST": "E", "WEST": "W"}
# Titles spell some suffixes out; permits and licenses use the abbreviation the warehouse's address key expects.
SUFFIX_MAP = {
    "AVENUE": "AVE",
    "STREET": "ST",
    "BOULEVARD": "BLVD",
    "DRIVE": "DR",
    "ROAD": "RD",
    "PLACE": "PL",
    "COURT": "CT",
    "PARKWAY": "PKWY",
    "TERR": "TER",
    "TERRACE": "TER",
    "LANE": "LN",
    "SQUARE": "SQ",
    "CIRCLE": "CIR",
    "HIGHWAY": "HWY",
    "EXPRESSWAY": "EXPY",
    "PLAZA": "PLZ",
}
# District codes as they appear in Chicago zoning text: RS-3, RT-4A, RM-5.5, B3-2, C1-3, DX-12, DR-10, M1-2,
# PMD 11, POS-1, and planned developments.
DISTRICT = r"(?:RS|RT|RM|B1|B2|B3|C1|C2|C3|DC|DX|DR|DS|M1|M2|M3|PMD|POS)\s*-?\s*[0-9]{0,2}(?:\.[0-9])?[A-Z]?"
PD_TEXT = r"(?:(?:Business|Commercial|Residential|Downtown|Manufacturing)\s+)?Planned\s+Development(?:\s+No\.?\s*[0-9]+)?"
FROM_TO_RE = re.compile(
    rf"\b({DISTRICT})\s+to\s+(?:a\s+|an\s+|the\s+)?({DISTRICT}|{PD_TEXT})(?![A-Z0-9])", re.IGNORECASE
)
PD_RE = re.compile(r"planned\s+development", re.IGNORECASE)


def _street(text: str) -> str:
    text = re.sub(r"\(.*?\)", " ", text)
    text = re.sub(r"\s+-\s+.*$", "", text)
    words = re.sub(r"[.,]", " ", text.upper()).split()
    while words and words[-1] in ("AND", "AMD", "OR"):
        words.pop()
    if words and words[-1] in SUFFIX_MAP:
        words[-1] = SUFFIX_MAP[words[-1]]
    return " ".join(words)


def parse_title(title: str) -> dict:
    """Pull map sheet, application number, address ranges and any districts out of a matter title.

    Returns {"map_no", "app_no", "type1", "planned_development", "from_district", "to_district",
    "addresses": [{"num_from", "num_to", "dir", "street"}]}. A range keeps its first number as the address key,
    like every other source in the warehouse. Titles that list several addresses ("... at 466 W Cermak Rd and
    2106-2124 S Canal St", also separated by commas or slashes) yield one entry per address. Intersections ("W
    Albion Ave and N Kedzie Ave") and areas yield none.
    """
    t = re.sub(r"\s+", " ", title or "").strip()
    m = MAP_RE.search(t)
    a = APP_RE.search(t)
    app = a.group(1).upper() if a else None
    tail = re.split(r"\s*-?\s*\bApp(?:lication)?\.?\s+No\b", t, maxsplit=1, flags=re.IGNORECASE)[0]
    start = ADDR_START_RE.search(tail)
    body = tail[start.start() :] if start else ""
    pieces: list[str] = []
    for piece in SEGMENT_SPLIT_RE.split(body.strip()):
        if not piece:
            continue
        if pieces and not piece[0].isdigit():
            pieces[-1] += " " + piece
        else:
            pieces.append(piece)
    addresses = []
    pending: list[tuple[int, int | None]] = []
    for piece in pieces:
        text = piece.strip()
        bare = BARE_NUMBER_RE.match(text)
        if bare:
            pending.append((int(bare.group(1)), int(bare.group(2)) if bare.group(2) else None))
            continue
        x = SEGMENT_RE.match(text)
        if not x:
            pending = []
            continue
        street = _street(x.group(4))
        direction = DIRECTIONS.get(x.group(3).upper(), x.group(3).upper())
        # "5531, 5533, 5535 and 5537 S Oakley Ave": bare numbers take the street of the next full address.
        for lo, hi in [*pending, (int(x.group(1)), int(x.group(2)) if x.group(2) else None)]:
            if street:
                addresses.append({"num_from": lo, "num_to": hi, "dir": direction, "street": street})
        pending = []
    ft = FROM_TO_RE.search(t)
    return {
        "map_no": re.sub(r"\s+", "", m.group(1)).upper() if m else None,
        "app_no": app,
        "type1": bool(app and app.endswith("T1")) or bool(re.search(r"\bType\s*1\b", t, re.IGNORECASE)),
        "planned_development": bool(PD_RE.search(t)),
        "from_district": re.sub(r"[\s-]+", "", ft.group(1)).upper() if ft else None,
        "to_district": re.sub(r"\s+", " ", ft.group(2)).strip().upper() if ft else None,
        "addresses": addresses,
    }


def write_flat(out_dir: Path = RAW) -> Path:
    """Flatten list pages to one JSONL line per (matter, address): the warehouse reads this file."""
    rows = []
    for r in list_matters(out_dir):
        parsed = parse_title(r.get("title") or "")
        base = {
            "matter_id": r["matterId"],
            "record_no": r.get("recordNumber"),
            "file_year": r.get("fileYear"),
            "title": re.sub(r"\s+", " ", r.get("title") or "").strip(),
            "intro_date": (r.get("introductionDate") or "")[:10] or None,
            "final_action_date": (r.get("finalActionDate") or "")[:10] or None,
            "status": r.get("status"),
            "sub_status": r.get("subStatus"),
            "legacy_status": r.get("legacyStatus"),
            "sponsor": r.get("filingSponsor"),
            "committee": r.get("committeReferral"),
            "map_no": parsed["map_no"],
            "app_no": parsed["app_no"],
            "type1": parsed["type1"],
            "planned_development": parsed["planned_development"],
            "from_district": parsed["from_district"],
            "to_district": parsed["to_district"],
        }
        addrs = parsed["addresses"] or [None]
        for i, a in enumerate(addrs):
            row = dict(base, addr_idx=i)
            if a:
                row.update(
                    addr_num=a["num_from"],
                    addr_num_to=a["num_to"],
                    addr_dir=a["dir"],
                    addr_street=a["street"],
                    addr_text=f"{a['num_from']} {a['dir']} {a['street']}",
                )
            rows.append(row)
    out = out_dir / "zoning_changes.jsonl"
    tmp = out.with_suffix(".tmp")
    tmp.write_text("\n".join(json.dumps(r, sort_keys=True) for r in rows) + "\n")
    tmp.rename(out)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", type=int, default=FIRST_YEAR, help="first fileYear to fetch")
    ap.add_argument("--details", type=int, default=0, help="also cache up to N per-matter pages")
    ap.add_argument("--parse-only", action="store_true", help="skip fetching; rebuild the flat file")
    args = ap.parse_args()
    if not args.parse_only:
        sync(RAW, args.since, args.details)
    out = write_flat(RAW)
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
