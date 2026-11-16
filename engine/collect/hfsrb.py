"""Illinois Health Facilities and Services Review Board (HFSRB) certificate-of-need projects.

Chicago's analog of the Georgia DCH weekly report: every CON and exemption project the Board lists.
Sources (public, no login; robots.txt allows generic agents):

1. The project-search listing, a JSON model the site's own page loads (one request): project number and name,
   year, status (Exempted / Non-Exempted), deemed-complete flag, link to the project page.
2. Per-project HTML pages (one request each, cached): received date, deadlines, board meeting date and
   links to the application, completeness letter, staff report and permit approval letter PDFs.
3. Optional (`--documents`): first page of the staff report or permit approval letter PDFs, which carry the
   project cost, facility, city, permit holders and a description naming equipment. Needs the `pypdf` package,
   which is not a project dependency; without it this step is skipped with a message.

Writes raw files to data/raw/hfsrb/ (gitignored) and a deterministic CSV, data/hfsrb-projects.csv, sorted by
project number. Polite: the User-Agent identifies the project, at most one request per second, robots.txt is
checked before every fetch.

    uv run python -m engine.collect.hfsrb                      # listing + pages for 2025 onward
    uv run python -m engine.collect.hfsrb --since 2022 --documents
"""

from __future__ import annotations

import argparse
import csv
import html
import io
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path

BASE = "https://hfsrb.illinois.gov"
LISTING = (
    BASE + "/content/soi/hfsrb/en/project/project-search/jcr:content/responsivegrid/container/container/"
    "contentfragmentlist.model.json"
)
UA = "BricklineResearchBot/0.1 (public-records research; +contact: founder)"
RAW = Path("data/raw/hfsrb")
OUT = Path("data/hfsrb-projects.csv")

DATE_FIELDS = {
    "projectReceivedDate": "received_date",
    "projectRequestPublicHearingDate": "hearing_request_deadline",
    "publicHearingDate": "public_hearing_date",
    "projectWrittenCommentDate": "written_comment_deadline",
    "meetingDateForConsideration": "board_meeting_date",
}

DOC_KINDS = [
    ("application_url", re.compile(r"^(exemption )?application", re.I)),
    ("completeness_letter_url", re.compile(r"completeness", re.I)),
    ("staff_report_url", re.compile(r"staff report|report for board", re.I)),
    (
        "approval_letter_url",
        re.compile(r"(permit|board|state board|exemption) approval letter|^approval letter", re.I),
    ),
]

EQUIPMENT = {
    "mri": r"\bMRI\b|magnetic resonance",
    "ct": r"\bCT\b(?! scan simul)|computed tomography|CT simulator",
    "linac": r"linear accelerator|\bLINAC\b|radiation therapy",
    "pet": r"\bPET\b|positron",
    "cath_lab": r"cardiac cath|catheterization|cath lab",
    "operating_rooms": r"operating room|surgical suite",
    "dialysis": r"dialysis|ESRD|end.stage renal",
    "robotic_surgery": r"robotic|da Vinci",
    "xray_imaging": r"x-ray|radiograph|mammograph|ultrasound",
}

COLUMNS = [
    "project_no",
    "project_name",
    "facility_name",
    "city_in_name",
    "project_year",
    "project_status",
    "deemed_complete",
    "name_mentions_chicago",
    "received_date",
    "hearing_request_deadline",
    "public_hearing_date",
    "written_comment_deadline",
    "board_meeting_date",
    "document_count",
    "application_url",
    "completeness_letter_url",
    "staff_report_url",
    "approval_letter_url",
    "doc_source",
    "doc_project_no",
    "doc_project_cost",
    "doc_facility",
    "doc_city",
    "doc_address",
    "doc_permit_holders",
    "doc_description",
    "doc_equipment_flags",
    "doc_completion_date",
    "page_url",
]


class Fetcher:
    def __init__(self, min_interval: float = 1.0) -> None:
        self.min_interval = min_interval
        self.last = 0.0
        self.robots = urllib.robotparser.RobotFileParser()
        self.robots_ok = False
        self.warned_no_pdf = False

    def _sleep(self) -> None:
        wait = self.min_interval - (time.monotonic() - self.last)
        if wait > 0:
            time.sleep(wait)
        self.last = time.monotonic()

    def load_robots(self) -> None:
        self._sleep()
        req = urllib.request.Request(BASE + "/robots.txt", headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=60) as resp:
            self.robots.parse(resp.read().decode("utf-8", "replace").splitlines())
        self.robots_ok = True

    def get(self, url: str, attempts: int = 4) -> bytes:
        if not self.robots_ok:
            self.load_robots()
        url = urllib.parse.quote(url, safe=":/%?&=,-._~()+")
        if not self.robots.can_fetch(UA, url):
            raise PermissionError(f"robots.txt disallows {url}")
        for attempt in range(attempts):
            self._sleep()
            try:
                req = urllib.request.Request(url, headers={"User-Agent": UA})
                with urllib.request.urlopen(req, timeout=120) as resp:
                    return resp.read()
            except (urllib.error.URLError, TimeoutError) as exc:
                if isinstance(exc, urllib.error.HTTPError) and exc.code in (403, 404):
                    raise
                if attempt == attempts - 1:
                    raise RuntimeError(f"download failed after {attempts} attempts: {url}") from exc
                time.sleep(4 * 2**attempt)
        raise AssertionError("unreachable")


class ElementParser(HTMLParser):
    """Collects `cmp-contentfragment__element--<key>` text and PDF links from a project page."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.fields: dict[str, list[str]] = {}
        self.docs: list[tuple[str, str]] = []
        self._key: str | None = None
        self._depth = 0
        self._href: str | None = None
        self._href_text: list[str] = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        cls = a.get("class") or ""
        m = re.search(r"cmp-contentfragment__element--(\w+)", cls)
        if m and tag == "div":
            self._key = m.group(1)
            self._depth = 1
            self.fields.setdefault(self._key, [])
        elif self._key and tag == "div":
            self._depth += 1
        if tag == "a" and (a.get("href") or "").lower().split("?")[0].endswith(".pdf"):
            self._href = a["href"]
            self._href_text = []

    def handle_endtag(self, tag):
        if tag == "div" and self._key:
            self._depth -= 1
            if self._depth <= 0:
                self._key = None
        if tag == "a" and self._href:
            label = re.sub(r"\s+", " ", "".join(self._href_text)).strip()
            if self._href.startswith("/content/dam"):
                self.docs.append((label, self._href))
            self._href = None

    def handle_data(self, data):
        if self._key:
            self.fields[self._key].append(data)
        if self._href is not None:
            self._href_text.append(data)


def parse_page(page_html: str) -> dict:
    p = ElementParser()
    p.feed(page_html)
    out: dict = {}
    for src, col in DATE_FIELDS.items():
        text = re.sub(r"\s+", " ", " ".join(p.fields.get(src, []))).strip()
        text = re.sub(
            r"^(Received Date|Deadline[^,]*?|HFSRB Meeting Date for Consideration|Public Hearing Date)\s+",
            "",
            text,
        )
        out[col] = _iso_date(text)
    out["documents"] = p.docs
    return out


def _iso_date(text: str) -> str:
    m = re.search(r"([A-Z][a-z]+ \d{1,2}, \d{4})", text)
    if not m:
        return ""
    try:
        return datetime.strptime(m.group(1), "%B %d, %Y").strftime("%Y-%m-%d")
    except ValueError:
        return ""


def split_name(name: str, link: str) -> tuple[str, str, str, str]:
    """(project_no, facility, city_in_name, name); listing typos ('26-0321') lose to the link's number."""
    name = html.unescape(name).strip()
    m = re.match(r"^(E-\d{3}-\d{2}|\d{2}-\d{3,4})\b[\s,.-]*(.*)$", name)
    num, rest = (m.group(1), m.group(2).strip()) if m else ("", name)
    slug = link.rsplit("project.", 1)[-1]
    lm = re.search(r"(?:^|-)(e-\d{3}-\d{2}|\d{2}-\d{3})(?=-|\.html|$)", slug, re.I)
    link_no = lm.group(1).upper() if lm else ""
    if not re.fullmatch(r"E-\d{3}-\d{2}|\d{2}-\d{3}", num):
        num = link_no or num
        if not m:
            rest = name
    elif link_no and link_no != num:
        num = link_no
    city = ""
    cm = re.match(r"^(.*\S),\s*([A-Za-z .'-]{3,30})$", rest)
    if cm and "," not in cm.group(2):
        rest, city = cm.group(1).strip(), cm.group(2).strip()
    return num, rest, city, name


def load_listing(fetcher: Fetcher, refresh: bool, log=print) -> list[dict]:
    RAW.mkdir(parents=True, exist_ok=True)
    path = RAW / "listing.json"
    if refresh or not path.exists():
        body = fetcher.get(LISTING)
        json.loads(body)
        path.write_bytes(body)
        log(f"  hfsrb listing: {len(body) / 1e3:.0f} KB")
    d = json.loads(path.read_text())
    return [x for x in d["listItems"] if "projectName" in x]


def page_path(link: str) -> Path:
    return RAW / "pages" / (re.sub(r"[^A-Za-z0-9._-]", "_", link.rsplit("/", 1)[-1]) or "page.html")


def fetch_page(fetcher: Fetcher, link: str) -> str | None:
    path = page_path(link)
    if path.exists():
        return path.read_text(encoding="utf-8", errors="replace")
    url = BASE + link.replace("/content/soi/hfsrb/en/", "/")
    try:
        body = fetcher.get(url)
    except urllib.error.HTTPError:
        return None
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_bytes(body)
    tmp.rename(path)
    return body.decode("utf-8", "replace")


def pick_doc(docs: list[tuple[str, str]], pattern: re.Pattern) -> str:
    for label, href in docs:
        if pattern.search(label):
            return BASE + urllib.parse.quote(urllib.parse.unquote(href), safe="/%")
    return ""


def pdf_header_fields(pdf: bytes) -> dict | None:
    """Header fields from the first pages of a staff report or permit approval letter; None without pypdf."""
    try:
        import pypdf
    except ImportError:
        return None
    try:
        reader = pypdf.PdfReader(io.BytesIO(pdf))
        flat = re.sub(
            r"\s+",
            " ",
            "\n".join((reader.pages[i].extract_text() or "") for i in range(min(2, len(reader.pages)))),
        )
    except Exception:
        return {}
    out: dict = {}
    pats = {
        "doc_project_no": r"PROJECT NO:\s*#?([E\d-]+)|Project Number:\s*#?([E\d-]+)",
        "doc_project_cost": r"PROJECT COST:\s*Original:\s*(\$[\d,]+)|Permit Amount:\s*(\$[\d,]+)",
        "doc_facility": r"FACILITY NAME:\s*(.+?)\s+CITY:|Facility Name:\s*(.+?)\s+Facility Address:",
        "doc_city": r"CITY:\s*([A-Za-z .]+?)\s+TYPE OF PROJECT",
        "doc_address": r"Facility Address:\s*(.+?)\s+(?:Permit Holders?|Applicants?):",
        "doc_permit_holders": r"(?:Permit Holders?|Applicants?):\s*(.+?)\s+Project Description:",
        "doc_description": (
            r"PROJECT DESCRIPTION:\s*(.+?)(?:\s+(?:Page \d+ of \d+|EXECUTIVE SUMMARY|The State Board Staff"
            r"|Information on this Application)|$)|Project Description:\s*(.+?)\s+Permit Amount:"
        ),
        "doc_completion_date": r"Project Completion Date:\s*([A-Za-z]+ \d+, \d{4})",
    }
    for key, pat in pats.items():
        m = re.search(pat, flat)
        if m:
            out[key] = next(g for g in m.groups() if g).strip()[:600]
    if "doc_city" not in out and out.get("doc_address"):
        addr = re.sub(r",?\s*(?:Illinois|IL)\b.*$", "", out["doc_address"]).strip(" ,")
        if "," in addr:
            out["doc_city"] = addr.rsplit(",", 1)[1].strip()
    if "doc_project_cost" not in out:
        m = re.search(r"cost of \$([\d,]+)", flat)
        if m:
            out["doc_project_cost"] = "$" + m.group(1)
    text = out.get("doc_description", "")
    flags = sorted(k for k, pat in EQUIPMENT.items() if re.search(pat, text, re.I))
    out["doc_equipment_flags"] = ";".join(flags)
    return out


def sync(
    since: int = 2025,
    documents: bool = False,
    refresh: bool = False,
    limit: int | None = None,
    log=print,
) -> list[dict]:
    fetcher = Fetcher()
    items = load_listing(fetcher, refresh, log)
    rows: list[dict] = []
    fetched = 0
    for it in items:
        link = it.get("meta", {}).get("dynamicPageLink", "")
        num, facility, city, name = split_name(it["projectName"], link)
        year = it.get("projectYear") or ""
        row = {c: "" for c in COLUMNS}
        row.update(
            project_no=num,
            project_name=name,
            facility_name=facility,
            city_in_name=city,
            project_year=year,
            project_status=it.get("projectStatus") or "",
            deemed_complete=(it.get("projectDeemedComplete") or "").lower(),
            name_mentions_chicago="yes" if re.search(r"chicago", name, re.I) else "",
            page_url=BASE + link.replace("/content/soi/hfsrb/en/", "/") if link else "",
            document_count=0,
        )
        if link and year.isdigit() and int(year) >= since and (limit is None or fetched < limit):
            had = page_path(link).exists()
            page_html = fetch_page(fetcher, link)
            fetched += 0 if had else 1
            if page_html:
                parsed = parse_page(page_html)
                for col in DATE_FIELDS.values():
                    row[col] = parsed[col]
                row["document_count"] = len(parsed["documents"])
                for col, pat in DOC_KINDS:
                    row[col] = pick_doc(parsed["documents"], pat)
                if documents:
                    _add_document_fields(fetcher, row, log)
        rows.append(row)
    rows.sort(key=lambda r: (r["project_no"] == "", r["project_no"], r["project_name"], r["page_url"]))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUT.with_suffix(".tmp")
    with tmp.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    tmp.rename(OUT)
    log(
        f"  hfsrb: {len(rows)} projects -> {OUT} "
        f"({sum(1 for r in rows if r['received_date'])} with page dates)"
    )
    return rows


def _add_document_fields(fetcher: Fetcher, row: dict, log) -> None:
    for kind, col in (("approval_letter", "approval_letter_url"), ("staff_report", "staff_report_url")):
        url = row[col]
        if not url:
            continue
        name = re.sub(r"[^A-Za-z0-9._-]", "_", urllib.parse.unquote(url).rsplit("/", 1)[-1])
        path = RAW / "docs" / f"{row['project_no']}-{kind}-{name}"[:180]
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            try:
                body = fetcher.get(url)
            except (urllib.error.HTTPError, RuntimeError):
                continue
            tmp = path.with_suffix(".tmp")
            tmp.write_bytes(body)
            tmp.rename(path)
        fields = pdf_header_fields(path.read_bytes())
        if fields is None:
            if not fetcher.warned_no_pdf:
                log("  hfsrb: pypdf is not installed; skipping document fields")
                fetcher.warned_no_pdf = True
            return
        if fields and fields.get("doc_project_no", row["project_no"]) != row["project_no"]:
            row["doc_source"] = f"mismatch:{kind}"
            continue
        if fields:
            row.update(fields)
            row["doc_source"] = kind
            return


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument(
        "--since", type=int, default=2025, help="fetch project pages for projects of this year and later"
    )
    ap.add_argument(
        "--documents", action="store_true", help="also read staff report / approval letter PDFs (needs pypdf)"
    )
    ap.add_argument("--refresh", action="store_true", help="re-download the listing")
    ap.add_argument("--limit", type=int, default=None, help="max project pages to download in this run")
    a = ap.parse_args()
    sync(a.since, a.documents, a.refresh, a.limit)


if __name__ == "__main__":
    main()
