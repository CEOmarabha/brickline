"""Probe public data sources and write a verification catalog (Deliverable A, 2026-11-16).

For every source in SOURCES this script makes a small, polite request (identified User-Agent, robots.txt
checked, >=1 second between requests to a host, `$limit=5` style samples, bytes capped), records what was
actually retrieved (HTTP status, rows, field names, newest record date) and writes
research/findings/source-verification-<date>.json and .md.

Standard library only. Usage:
    python3 research/probes/source_check.py                  # probe everything, write findings
    python3 research/probes/source_check.py --only chi-permits seattle-permits
    python3 research/probes/source_check.py --fetch URL      # one polite GET, print a summary (exploration)

Never bypasses logins, paywalls, CAPTCHAs, anti-bot blocks or robots.txt: a blocked request is recorded as
blocked. PDF text is only read when `pypdf` happens to be importable (it is not a project dependency); the
catalog states whether it was.

Output determinism: sorted keys, no wall-clock timestamps except the run date (`--date`, default
2026-11-16 for this deliverable). Probe values change only when the sources change.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONTACT = os.environ.get("BRICKLINE_CONTACT_EMAIL", "")
UA = (
    "BricklineResearchBot/0.1 (public-records research; +contact: founder"
    + (f" {CONTACT}" if CONTACT else "")
    + ")"
)
MIN_INTERVAL = 1.0
DEFAULT_MAX_BYTES = 1_500_000
RUN_DATE = "2026-11-16"


# --------------------------------------------------------------------------------------------------
# Polite HTTP
# --------------------------------------------------------------------------------------------------


class Fetcher:
    def __init__(self) -> None:
        self.last: dict[str, float] = {}
        self.robots: dict[str, tuple[urllib.robotparser.RobotFileParser | None, dict]] = {}
        self.crawl_delay: dict[str, float] = {}

    def _wait(self, host: str) -> None:
        gap = max(MIN_INTERVAL, self.crawl_delay.get(host, 0.0))
        elapsed = time.monotonic() - self.last.get(host, 0.0)
        if elapsed < gap:
            time.sleep(gap - elapsed)
        self.last[host] = time.monotonic()

    def _raw(
        self, url: str, headers: dict | None, max_bytes: int, timeout: int, data: bytes | None = None
    ) -> dict:
        host = urllib.parse.urlsplit(url).netloc
        self._wait(host)
        req_headers = {"User-Agent": UA, "Accept": "*/*", "Accept-Encoding": "identity"}
        req_headers.update(headers or {})
        req = urllib.request.Request(url, headers=req_headers, data=data)
        out: dict = {"url": url, "status": None, "content_type": None, "bytes": 0, "error": None}
        try:
            resp = urllib.request.urlopen(req, timeout=timeout)
        except urllib.error.HTTPError as exc:
            resp = exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            out["error"] = f"{type(exc).__name__}: {exc}"[:200]
            out["body"] = b""
            return out
        try:
            body = resp.read(max_bytes + 1)
        except (TimeoutError, OSError) as exc:
            body = b""
            out["error"] = f"{type(exc).__name__}: {exc}"[:200]
        out["status"] = resp.status if hasattr(resp, "status") else resp.code
        out["content_type"] = (resp.headers.get("Content-Type") or "").split(";")[0].strip() or None
        out["headers"] = {k.lower(): v for k, v in resp.headers.items()}
        out["truncated"] = len(body) > max_bytes
        out["body"] = body[:max_bytes]
        out["bytes"] = len(out["body"])
        out["final_url"] = resp.geturl() if hasattr(resp, "geturl") else url
        return out

    def robots_for(self, url: str) -> tuple[bool | None, str]:
        parts = urllib.parse.urlsplit(url)
        base = f"{parts.scheme}://{parts.netloc}"
        if base not in self.robots:
            r = self._raw(base + "/robots.txt", None, 300_000, 30)
            status = r["status"]
            rp: urllib.robotparser.RobotFileParser | None = urllib.robotparser.RobotFileParser()
            if (
                status == 200
                and r["content_type"] in (None, "text/plain", "text/html", "application/octet-stream")
                and (b"user-agent" in r["body"].lower())
            ):
                rp.parse(r["body"].decode("utf-8", "replace").splitlines())
                delay = rp.crawl_delay(UA)
                if delay:
                    self.crawl_delay[parts.netloc] = float(delay)
                note = "robots.txt 200" + (f", crawl-delay {delay}s honored" if delay else "")
            elif status in (401, 403):
                rp = None
                note = f"robots.txt {status}: treated as no-crawl (not bypassed)"
            elif status is None:
                rp = urllib.robotparser.RobotFileParser()
                rp.allow_all = True
                note = f"robots.txt unreachable ({r['error']}): treated as allowed"
            else:
                rp = urllib.robotparser.RobotFileParser()
                rp.parse([])
                note = f"robots.txt {status} / no rules: allowed"
            self.robots[base] = (rp, {"note": note})
        rp, meta = self.robots[base]
        if rp is None:
            return False, meta["note"]
        allowed = rp.can_fetch(UA, url)
        return allowed, meta["note"] + ("" if allowed else "; path disallowed")

    def get(
        self,
        url: str,
        headers: dict | None = None,
        max_bytes: int = DEFAULT_MAX_BYTES,
        timeout: int = 60,
        check_robots: bool = True,
        retries: int = 1,
        data: bytes | None = None,
    ) -> dict:
        if check_robots:
            allowed, note = self.robots_for(url)
            if allowed is False:
                return {
                    "url": url,
                    "status": None,
                    "content_type": None,
                    "bytes": 0,
                    "body": b"",
                    "error": "skipped: " + note,
                    "robots": note,
                    "skipped": True,
                }
        else:
            note = "robots.txt not applicable (documented public API/file endpoint)"
        for attempt in range(retries + 1):
            r = self._raw(url, headers, max_bytes, timeout, data=data)
            if r["status"] is not None and r["status"] < 500 and not r["error"]:
                break
            if attempt < retries:
                time.sleep(3)
        r["robots"] = note
        return r


def req_summary(r: dict) -> dict:
    """The part of a response that goes into the catalog (no body)."""
    out = {"url": r["url"], "status": r["status"], "content_type": r["content_type"], "bytes": r["bytes"]}
    if r.get("error"):
        out["error"] = r["error"]
    if r.get("truncated"):
        out["truncated_at_cap"] = True
    if r.get("robots") and "not applicable" not in r["robots"]:
        out["robots"] = r["robots"]
    return out


def jbody(r: dict):
    try:
        return json.loads(r["body"].decode("utf-8", "replace"))
    except (ValueError, KeyError):
        return None


def text_of(html: str) -> str:
    html = re.sub(r"(?is)<(script|style).*?</\1>", " ", html)
    html = re.sub(r"<[^>]+>", " ", html)
    import html as htmlmod

    return re.sub(r"\s+", " ", htmlmod.unescape(html)).strip()


def short(v, n: int = 70):
    if isinstance(v, str):
        return v if len(v) <= n else v[: n - 1] + "…"
    if isinstance(v, dict):
        return {k: short(x, n) for k, x in list(v.items())[:6]}
    return v


def day(s) -> str | None:
    if s is None:
        return None
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", str(s))
    if m:
        return m.group(0)
    m8 = re.fullmatch(r"(\d{4})(\d{2})(\d{2})", str(s))
    if m8:
        return f"{m8.group(1)}-{m8.group(2)}-{m8.group(3)}"
    m = re.match(r"(\d{2})/(\d{2})/(\d{4})", str(s))
    if m:
        return f"{m.group(3)}-{m.group(1)}-{m.group(2)}"
    return str(s)[:10]


def http_day(v: str | None) -> str | None:
    if not v:
        return None
    try:
        from email.utils import parsedate_to_datetime

        return parsedate_to_datetime(v).strftime("%Y-%m-%d")
    except (TypeError, ValueError):
        return None


def epoch_day(v) -> str | None:
    try:
        return datetime.fromtimestamp(int(v), UTC).strftime("%Y-%m-%d")
    except (TypeError, ValueError, OSError):
        return None


def pdf_text(body: bytes, pages: int = 2) -> str | None:
    """First pages of PDF text via pypdf if present; None when no PDF library is available."""
    try:
        import pypdf
    except ImportError:
        return None
    try:
        rd = pypdf.PdfReader(io.BytesIO(body))
        return "\n".join((rd.pages[i].extract_text() or "") for i in range(min(pages, len(rd.pages))))
    except Exception as exc:  # malformed or scanned PDFs
        return f"[pdf text extraction failed: {type(exc).__name__}]"


def pdf_pages(body: bytes) -> int | None:
    n = len(re.findall(rb"/Type\s*/Page(?!s)", body))
    return n or None


# --------------------------------------------------------------------------------------------------
# Probe kinds: each returns a dict with ok(bool) and evidence
# --------------------------------------------------------------------------------------------------


def probe_socrata(
    F: Fetcher,
    domain: str,
    dataset: str,
    date_field: str | None = None,
    order_field: str | None = None,
    where: str | None = None,
    redact: tuple[str, ...] = (),
    group_field: str | tuple[str, ...] | None = None,
    fields_of_interest: tuple[str, ...] = (),
    extra_dates: tuple[str, ...] = (),
) -> dict:
    base = f"https://{domain}"
    reqs, notes = [], {}
    meta_r = F.get(f"{base}/api/views/{dataset}.json", check_robots=False, max_bytes=3_000_000)
    reqs.append(req_summary(meta_r))
    meta = jbody(meta_r) or {}
    cols = [c.get("fieldName") for c in meta.get("columns", [])] if isinstance(meta, dict) else []
    if isinstance(meta, dict) and meta.get("name"):
        lic = meta.get("license") or {}
        notes.update(
            {
                "dataset_name": meta.get("name"),
                "rows_updated_at": epoch_day(meta.get("rowsUpdatedAt")),
                "license": lic.get("name") if isinstance(lic, dict) else None,
                "license_terms_link": lic.get("termsLink") if isinstance(lic, dict) else None,
                "attribution": meta.get("attribution"),
                "column_count": len(cols),
                "description": short((meta.get("description") or "").replace("\n", " "), 240),
            }
        )
    q = {"$limit": "5"}
    if where:
        q["$where"] = where
    if order_field or date_field:
        q["$order"] = f"{order_field or date_field} DESC"
    sample_r = F.get(f"{base}/resource/{dataset}.json?{urllib.parse.urlencode(q)}", check_robots=False)
    reqs.append(req_summary(sample_r))
    rows = jbody(sample_r)
    rows = rows if isinstance(rows, list) else []
    cq = {"$select": "count(*)"}
    if where:
        cq["$where"] = where
    count_r = F.get(f"{base}/resource/{dataset}.json?{urllib.parse.urlencode(cq)}", check_robots=False)
    reqs.append(req_summary(count_r))
    cj = jbody(count_r)
    total = None
    if isinstance(cj, list) and cj and "count" in cj[0]:
        total = int(cj[0]["count"])
    latest = None
    if date_field:
        mq = {"$select": f"max({date_field}) as m"}
        if where:
            mq["$where"] = where
        m_r = F.get(f"{base}/resource/{dataset}.json?{urllib.parse.urlencode(mq)}", check_robots=False)
        reqs.append(req_summary(m_r))
        mj = jbody(m_r)
        if isinstance(mj, list) and mj and mj[0].get("m"):
            latest = day(mj[0]["m"])
        mn = {"$select": f"min({date_field}) as m"}
        mn_r = F.get(f"{base}/resource/{dataset}.json?{urllib.parse.urlencode(mn)}", check_robots=False)
        reqs.append(req_summary(mn_r))
        nj = jbody(mn_r)
        if isinstance(nj, list) and nj and nj[0].get("m"):
            notes["earliest_record_date"] = day(nj[0]["m"])
    for col in extra_dates:
        eq = {"$select": f"max({col}) as m"}
        if where:
            eq["$where"] = where
        e_r = F.get(f"{base}/resource/{dataset}.json?{urllib.parse.urlencode(eq)}", check_robots=False)
        reqs.append(req_summary(e_r))
        ej = jbody(e_r)
        if isinstance(ej, list) and ej and ej[0].get("m"):
            notes.setdefault("latest_by_field", {})[col] = day(ej[0]["m"])
    groups = (group_field,) if isinstance(group_field, str) else (group_field or ())
    for gf in groups:
        gq = {"$select": f"{gf},count(*) as n", "$group": gf, "$order": "n DESC", "$limit": "12"}
        if where:
            gq["$where"] = where
        g_r = F.get(f"{base}/resource/{dataset}.json?{urllib.parse.urlencode(gq)}", check_robots=False)
        reqs.append(req_summary(g_r))
        gj = jbody(g_r)
        if isinstance(gj, list):
            notes[f"top_{gf}"] = {str(x.get(gf)): int(x["n"]) for x in gj if "n" in x}
    sample_fields = sorted({k for r in rows for k in r if not k.startswith(":@")}) if rows else []
    rec = {
        k: short(v)
        for k, v in (rows[0].items() if rows else [])
        if k not in redact and not k.startswith(":@")
    }
    fi = {k: rec.get(k) for k in fields_of_interest if k in rec}
    return {
        "ok": bool(rows) and sample_r["status"] == 200,
        "requests": reqs,
        "rows_retrieved": len(rows),
        "total_records": total,
        "sample_fields": sample_fields or [c for c in cols if c and not c.startswith(":@")],
        "sample_record": fi or dict(list(rec.items())[:10]),
        "latest_record_date": latest,
        "details": notes,
    }


def probe_http(
    F: Fetcher,
    url: str,
    expect: tuple[str, ...] = (),
    headers: dict | None = None,
    max_bytes: int = DEFAULT_MAX_BYTES,
    check_robots: bool = True,
    ok_status: tuple[int, ...] = (200,),
    findings: dict | None = None,
) -> dict:
    """GET one URL. `expect` are regex patterns that must appear in the body (text) for ok."""
    r = F.get(url, headers=headers, max_bytes=max_bytes, check_robots=check_robots)
    text = r["body"].decode("utf-8", "replace") if r["body"] else ""
    visible = text_of(text) if text else ""
    hits = {p: bool(re.search(p, visible, re.I) or re.search(p, text, re.I)) for p in expect}
    ok = r["status"] in ok_status and all(hits.values())
    details = {"title": (re.search(r"(?is)<title[^>]*>(.*?)</title>", text) or [None, None])[1]}
    if details["title"]:
        details["title"] = short(re.sub(r"\s+", " ", details["title"]).strip(), 110)
    else:
        details.pop("title")
    if hits:
        details["expected_patterns_found"] = hits
    if r.get("headers"):
        for h in ("last-modified", "content-disposition", "content-length"):
            if r["headers"].get(h):
                details[h] = r["headers"][h]
    out = {"ok": ok, "requests": [req_summary(r)], "details": details}
    return out


def strip_private(p: dict) -> dict:
    return {k: v for k, v in p.items() if not k.startswith("_")}


# --------------------------------------------------------------------------------------------------
# Custom probes
# --------------------------------------------------------------------------------------------------

HFSRB = "https://hfsrb.illinois.gov"
HFSRB_LIST = (
    HFSRB + "/content/soi/hfsrb/en/project/project-search/jcr:content/responsivegrid/container/container/"
    "contentfragmentlist.model.json"
)


def hfsrb_items(F: Fetcher) -> tuple[dict, list[dict]]:
    r = F.get(HFSRB_LIST, max_bytes=4_000_000)
    d = jbody(r) or {}
    items = [x for x in d.get("listItems", []) if "projectName" in x]
    return r, items


def probe_hfsrb_list(F: Fetcher) -> dict:
    r, items = hfsrb_items(F)
    years: dict[str, int] = {}
    status: dict[str, int] = {}
    for x in items:
        years[x.get("projectYear") or "none"] = years.get(x.get("projectYear") or "none", 0) + 1
        status[x.get("projectStatus") or "none"] = status.get(x.get("projectStatus") or "none", 0) + 1
    chi = [x for x in items if re.search(r"chicago", x["projectName"], re.I)]
    nums = sorted(x["projectName"] for x in items)
    return {
        "ok": r["status"] == 200 and len(items) > 500,
        "requests": [req_summary(r)],
        "rows_retrieved": len(items),
        "total_records": len(items),
        "sample_fields": [
            "projectName",
            "projectYear",
            "projectStatus",
            "projectDeemedComplete",
            "meta.dynamicPageLink",
        ],
        "sample_record": {k: short(v) for k, v in items[-1].items()} if items else {},
        "latest_record_date": None,
        "details": {
            "by_year": dict(sorted(years.items())),
            "by_status": dict(sorted(status.items())),
            "names_mentioning_chicago": len(chi),
            "first_by_name": nums[:2],
            "note": "listing has no dates, costs, applicants or equipment; each project has a detail page with dates and PDFs",
        },
    }


def project_link(items: list[dict], number: str) -> str | None:
    for x in items:
        if x["projectName"].startswith(number) or number in x.get("meta", {}).get("dynamicPageLink", ""):
            link = x["meta"]["dynamicPageLink"]
            return HFSRB + link.replace("/content/soi/hfsrb/en/", "/")
    return None


def parse_hfsrb_page(html: str) -> dict:
    out: dict = {"fields": {}, "documents": []}
    for m in re.finditer(r'cmp-contentfragment__element--(\w+)"[^>]*>(.*?)</div>\s*</dl>', html, flags=re.S):
        val = text_of(m.group(2))
        if val:
            out["fields"][m.group(1)] = val
    for m in re.finditer(r'<a[^>]+href="(/content/dam[^"]+\.pdf)"[^>]*>(.*?)</a>', html, flags=re.S):
        out["documents"].append({"label": text_of(m.group(2)), "path": urllib.parse.unquote(m.group(1))})
    return out


HFSRB_SAMPLE_PROJECTS = ("26-032", "26-040", "25-025", "26-003", "25-048")


def probe_hfsrb_pages(F: Fetcher) -> dict:
    _, items = hfsrb_items(F)
    reqs, pages = [], {}
    for num in HFSRB_SAMPLE_PROJECTS:
        url = project_link(items, num)
        if not url:
            pages[num] = {"error": "not in listing"}
            continue
        r = F.get(url)
        reqs.append(req_summary(r))
        pages[num] = (
            parse_hfsrb_page(r["body"].decode("utf-8", "replace"))
            if r["status"] == 200
            else {"status": r["status"]}
        )
    ok = sum(1 for p in pages.values() if p.get("documents")) >= 3
    fields = sorted({k for p in pages.values() for k in p.get("fields", {})})
    return {
        "ok": ok,
        "requests": reqs,
        "rows_retrieved": len(pages),
        "sample_fields": fields,
        "sample_record": {
            k: {"fields": v.get("fields"), "documents": [d["label"] for d in v.get("documents", [])]}
            for k, v in list(pages.items())[:3]
        },
        "latest_record_date": None,
        "details": {"pages_with_documents": sum(1 for p in pages.values() if p.get("documents"))},
        "_pages": pages,
    }


def probe_hfsrb_docs(F: Fetcher) -> dict:
    """Sample 5 PDFs (staff reports, permit approval letters) and extract header fields when pypdf is present."""
    _, items = hfsrb_items(F)
    plan = [
        ("26-032", "Staff Report"),
        ("25-025", "Staff Report"),
        ("26-003", "Staff Report"),
        ("26-040", "Approval Letter"),
        ("25-048", "Approval Letter"),
    ]
    reqs, docs = [], []
    have_pdf = pdf_text(b"%PDF-1.4", 1) is not None
    for num, kind in plan:
        url = project_link(items, num)
        if not url:
            continue
        page = F.get(url)
        reqs.append(req_summary(page))
        parsed = parse_hfsrb_page(page["body"].decode("utf-8", "replace"))
        doc = next((d for d in parsed["documents"] if kind.lower() in d["label"].lower()), None)
        if not doc:
            docs.append({"project": num, "kind": kind, "error": "no such document link on the project page"})
            continue
        r = F.get(HFSRB + urllib.parse.quote(doc["path"]), max_bytes=8_000_000, timeout=120)
        reqs.append(req_summary(r))
        rec = {
            "project": num,
            "kind": kind,
            "label": doc["label"],
            "status": r["status"],
            "bytes": r["bytes"],
            "pdf_pages_approx": pdf_pages(r["body"]) if r["body"] else None,
        }
        txt = pdf_text(r["body"], 3) if r["status"] == 200 and not r.get("truncated") else None
        if txt:
            flat = re.sub(r"\s+", " ", txt)
            ex = {}
            for key, pat in {
                "project_no": r"PROJECT NO:\s*([E\d-]+)|Project Number:\s*([E\d-]+)",
                "cost": r"PROJECT COST:\s*Original:\s*(\$[\d,]+)|Permit Amount:\s*(\$[\d,]+)",
                "facility": r"FACILITY NAME:\s*(.+?)\s+CITY:|Facility Name:\s*(.+?)\s+Facility Address:",
                "city": r"CITY:\s*([A-Za-z .]+?)\s+TYPE OF PROJECT",
                "board_meeting": r"BOARD MEETING:\s*([A-Za-z]+ \d+, \d{4})",
                "permit_holders": r"Permit Holders?:\s*(.+?)\s+Project Description:",
                "description": r"Project Description:\s*(.+?)\s+Permit Amount:",
                "completion": r"Project Completion Date:\s*([A-Za-z]+ \d+, \d{4})",
            }.items():
                m = re.search(pat, flat)
                if m:
                    ex[key] = short(next(g for g in m.groups() if g), 110)
            rec["extracted"] = ex
        docs.append(rec)
    return {
        "ok": any(d.get("status") == 200 for d in docs),
        "requests": reqs,
        "rows_retrieved": len(docs),
        "sample_fields": [
            "project_no",
            "cost",
            "facility",
            "city",
            "board_meeting",
            "permit_holders",
            "description",
            "completion",
        ],
        "sample_record": {d["project"] + " " + d["kind"]: d.get("extracted", {}) for d in docs[:3]},
        "latest_record_date": None,
        "details": {"pdf_text_library_available": have_pdf, "documents": docs},
    }


def probe_ga_tracking(F: Fetcher) -> dict:
    page_url = "https://dch.georgia.gov/divisionsoffices/office-health-planning/certificate-need-con/con-tracking-report"
    page = F.get(page_url, max_bytes=2_000_000)
    reqs = [req_summary(page)]
    html = page["body"].decode("utf-8", "replace")
    links = sorted(set(re.findall(r'href="(/document/report/[^"]+/download)"', html)))
    details: dict = {"report_links_on_page": links}
    rec: dict = {}
    pdf_ok = False
    if links:
        r = F.get("https://dch.georgia.gov" + links[0], max_bytes=4_000_000, timeout=120)
        reqs.append(req_summary(r))
        pdf_ok = r["status"] == 200 and r["content_type"] == "application/pdf"
        details["file"] = (r.get("headers") or {}).get("content-disposition")
        details["last_modified"] = (r.get("headers") or {}).get("last-modified")
        txt = pdf_text(r["body"], 40) if pdf_ok else None
        details["pdf_text_library_available"] = pdf_text(b"%PDF-1.4", 1) is not None
        if txt and not txt.startswith("[pdf text extraction failed"):
            flat = re.sub(r"\s+", " ", txt)
            m = re.search(r"([A-Z][a-z]+ \d+, \d{4}) – ([A-Z][a-z]+ \d+, \d{4})", flat)
            details["report_period"] = f"{m.group(1)} – {m.group(2)}" if m else None
            details["project_ids"] = {
                "letters_of_intent": len(set(re.findall(r"LOI\d{7}", flat))),
                "applications": len(set(re.findall(r"(?<![\w-])20\d\d-\d{3}(?![\w-])", flat))),
            }
            details["records_with_estimated_cost"] = len(re.findall(r"Estimated Cost: \$[\d,]+", flat))
            details["records_with_site"] = len(re.findall(r"Site: ", flat))
            details["records_with_contact"] = len(re.findall(r"Contact: ", flat))
            m = re.search(r"(LOI\d{7}) (.+?) (?:Establishment|Expansion|Replacement|Addition)", flat)
            ex = re.search(
                r"(2026-\d{3}) (.{5,90}?) (?:Establishment|Expansion) of ([A-Za-z ]+?) Service.{0,40}? Filed: (\S+) Deemed Complete: (\S+).*?Site: (.{5,90}?)\) .*?Estimated Cost: (\$[\d,]+)",
                flat,
            )
            if ex:
                rec = {
                    "id": ex.group(1),
                    "applicant": short(ex.group(2), 60),
                    "service": ex.group(3),
                    "filed": ex.group(4),
                    "deemed_complete": ex.group(5),
                    "site": short(ex.group(6), 80),
                    "estimated_cost": ex.group(7),
                }
    ok = bool(links) and pdf_ok
    cdx = F.get(
        "https://web.archive.org/cdx/search/cdx?url=dch.georgia.gov/document/report/*tracking-report*/download&output=json&limit=40&filter=statuscode:200&collapse=urlkey",
        check_robots=False,
        timeout=90,
    )
    reqs.append(req_summary(cdx))
    cj = jbody(cdx)
    details["wayback_archived_report_urls"] = (len(cj) - 1) if isinstance(cj, list) and cj else 0
    return {
        "ok": ok,
        "requests": reqs,
        "rows_retrieved": 1 if ok else 0,
        "sample_fields": [
            "LOI id",
            "application id",
            "applicant",
            "service/project type",
            "filed",
            "deemed complete",
            "decision deadline",
            "site (county)",
            "contact + phone",
            "estimated cost",
        ],
        "sample_record": rec,
        "latest_record_date": None,
        "details": details,
    }


def probe_cms(F: Fetcher, uuid: str, flt: str, interest: tuple[str, ...] = (), note: str = "") -> dict:
    base = f"https://data.cms.gov/data-api/v1/dataset/{uuid}"
    flt = flt.replace(" ", "%20")
    q = f"?size=3&{flt}" if flt else "?size=3"
    r = F.get(base + "/data" + q)
    s = F.get(base + "/data/stats" + ("?" + flt if flt else ""))
    rows = jbody(r)
    rows = rows if isinstance(rows, list) else []
    st = jbody(s) or {}
    keys = sorted(rows[0].keys()) if rows else []
    rec = {k: short(rows[0].get(k)) for k in interest if rows and k in rows[0]}
    return {
        "ok": r["status"] == 200 and bool(rows),
        "requests": [req_summary(r), req_summary(s)],
        "rows_retrieved": len(rows),
        "total_records": st.get("found_rows"),
        "sample_fields": keys,
        "sample_record": rec or (dict(list(rows[0].items())[:8]) if rows else {}),
        "latest_record_date": None,
        "details": {"dataset_rows_all_states": st.get("total_rows"), "field_count": len(keys), "note": note},
    }


def probe_nppes_api(F: Fetcher) -> dict:
    r = F.get(
        "https://npiregistry.cms.hhs.gov/api/?version=2.1&state=IL&city=CHICAGO&enumeration_type=NPI-2&limit=3"
    )
    d = jbody(r) or {}
    res = d.get("results", []) if isinstance(d, dict) else []
    first = res[0] if res else {}
    basic = first.get("basic", {})
    return {
        "ok": r["status"] == 200 and bool(res),
        "requests": [req_summary(r)],
        "rows_retrieved": len(res),
        "total_records": None,
        "sample_fields": sorted(first.keys()) + ["basic." + k for k in sorted(basic.keys())],
        "sample_record": {
            "enumeration_date": basic.get("enumeration_date"),
            "last_updated": basic.get("last_updated"),
            "organization_name": short(basic.get("organization_name") or ""),
            "taxonomy": short((first.get("taxonomies") or [{}])[0].get("desc") or ""),
        },
        "latest_record_date": None,
        "details": {"limits": "query used: state, city, organization type; paging limits not tested"},
    }


def probe_range(F: Fetcher, url: str, page_url: str | None = None) -> dict:
    """Confirm a large bulk file exists without downloading it (Range request for 200 bytes)."""
    reqs = []
    if page_url and not url:
        page = F.get(page_url)
        reqs.append(req_summary(page))
        links = re.findall(
            r'href=["\']([^"\']*NPPES_Data_Dissemination_[A-Za-z]+_\d{4}_V2\.zip)["\']',
            page["body"].decode("utf-8", "replace"),
        )
        url = urllib.parse.urljoin(page_url, links[0]) if links else ""
    if not url:
        return {"ok": False, "requests": reqs, "details": {"error": "no file link found"}}
    r = F.get(url, headers={"Range": "bytes=0-199"}, max_bytes=400, check_robots=False)
    reqs.append(req_summary(r))
    h = r.get("headers") or {}
    m = re.search(r"/(\d+)$", h.get("content-range", ""))
    return {
        "ok": r["status"] in (200, 206),
        "requests": reqs,
        "details": {
            "file": url.rsplit("/", 1)[-1],
            "total_bytes": int(m.group(1)) if m else None,
            "last_modified": http_day(h.get("last-modified")),
            "range_supported": r["status"] == 206,
        },
    }


def probe_elms(F: Fetcher) -> dict:
    base = "https://api.chicityclerkelms.chicago.gov/matter"
    flt = "matterCategory eq 'ZONING RECLASSIFICATIONS'"
    reqs = []
    newest = F.get(
        f"{base}?{urllib.parse.urlencode({'top': 100, 'sort': 'introductionDate desc', 'filter': flt})}",
        check_robots=False,
        max_bytes=4_000_000,
    )
    oldest = F.get(
        f"{base}?{urllib.parse.urlencode({'top': 1, 'sort': 'introductionDate asc', 'filter': flt})}",
        check_robots=False,
    )
    sch = F.get(
        f"{base}?{urllib.parse.urlencode({'top': 3, 'search': 'Planned Development'})}", check_robots=False
    )
    reqs = [req_summary(newest), req_summary(oldest), req_summary(sch)]
    nd, od, sd = jbody(newest) or {}, jbody(oldest) or {}, jbody(sch) or {}
    rows = nd.get("data", []) if isinstance(nd, dict) else []
    sample = [
        {
            "record": m.get("recordNumber"),
            "introduced": day(m.get("introductionDate")),
            "status": m.get("status"),
            "title": short(m.get("title") or "", 120),
        }
        for m in rows[:2]
    ]
    pd_in_titles = sum(1 for m in rows if re.search(r"planned development", m.get("title") or "", re.I))
    return {
        "ok": bool(rows),
        "requests": reqs,
        "rows_retrieved": len(rows),
        "total_records": (nd.get("meta") or {}).get("count") if isinstance(nd, dict) else None,
        "sample_fields": sorted(rows[0].keys()) if rows else [],
        "sample_record": sample,
        "latest_record_date": max((x["introduced"] for x in sample if x["introduced"]), default=None),
        "details": {
            "query": "matterCategory = ZONING RECLASSIFICATIONS (Zoning Reclassification Map No. at <address> - App No. <zoning application number>)",
            "earliest_introduced": day(((od.get("data") or [{}])[0]).get("introductionDate"))
            if isinstance(od, dict)
            else None,
            "planned_development_in_newest_100_titles": pd_in_titles,
            "free_text_search_planned_development_matches": (sd.get("meta") or {}).get("count")
            if isinstance(sd, dict)
            else None,
            "note": "introduction dates can be future council-meeting dates; the free-text search matches any text, so Planned Development ordinances are not isolated by it",
        },
    }


def probe_echo(F: Fetcher) -> dict:
    cols = "qcolumns=1,3,4,5,6,8,11,14,23"
    base = "https://echodata.epa.gov/echo/echo_rest_services"
    r = F.get(
        f"{base}.get_facilities?output=JSON&p_st=IL&p_co=COOK&p_act=Y&p_med=A&{cols}", check_robots=False
    )
    d = (jbody(r) or {}).get("Results", {})
    reqs = [req_summary(r)]
    rows, fields = [], []
    qid = d.get("QueryID")
    if qid:
        q = F.get(
            f"{base}.get_qid?qid={qid}&pageno=1&pagesize=5&output=JSON&{cols}",
            check_robots=False,
            max_bytes=4_000_000,
        )
        reqs.append(req_summary(q))
        rows = ((jbody(q) or {}).get("Results") or {}).get("Facilities", [])[:5]
        fields = sorted(rows[0].keys()) if rows else []
    return {
        "ok": bool(rows),
        "requests": reqs,
        "rows_retrieved": len(rows),
        "total_records": int(d["QueryRows"]) if d.get("QueryRows") else None,
        "sample_fields": fields,
        "sample_record": {
            k: short(rows[0].get(k)) for k in ("FacCity", "FacZip", "FacEPARegion") if rows and k in rows[0]
        },
        "latest_record_date": None,
        "details": {
            "query": "Cook County IL, active facilities with an air (CAA) program ID",
            "note": "the get_qid page returns about 1 MB even with pagesize=5 (ignored by the service); only 5 rows are kept here; the get_facilities summary also reports inspection and violation counts",
            "summary_counts": {
                k: d.get(k) for k in ("QueryRows", "CVRows", "INSPRows", "FEARows", "TotalPenalties")
            },
        },
    }


def probe_census_bfs(F: Fetcher) -> dict:
    r = F.get("https://www.census.gov/econ/bfs/csv/bfs_monthly.csv", max_bytes=3_000_000)
    txt = r["body"].decode("utf-8", "replace")
    rows = list(csv.DictReader(io.StringIO(txt)))
    tot = [
        x
        for x in rows
        if x["geo"] == "US" and x["naics_sector"] == "TOTAL" and x["series"] == "BA_BA" and x["sa"] == "U"
    ]
    last = None
    if tot:
        y = max(int(x["year"]) for x in tot)
        row = next(x for x in tot if int(x["year"]) == y)
        months = [m for m in ("jan feb mar apr may jun jul aug sep oct nov dec".split()) if row.get(m)]
        last = (
            f"{y}-{('jan feb mar apr may jun jul aug sep oct nov dec'.split().index(months[-1]) + 1):02d}"
            if months
            else str(y)
        )
    geos = sorted({x["geo"] for x in rows})
    return {
        "ok": r["status"] == 200 and bool(rows),
        "requests": [req_summary(r)],
        "rows_retrieved": len(rows),
        "sample_fields": list(rows[0].keys()) if rows else [],
        "sample_record": tot[-1] if tot else {},
        "latest_record_date": last,
        "details": {
            "geographies_in_file": len(geos),
            "has_il": "IL" in geos,
            "has_county_or_metro": any(len(g) > 2 for g in geos if g != "US"),
            "series": sorted({x["series"] for x in rows})[:12],
            "file_truncated_at_cap": bool(r.get("truncated")),
        },
    }


def probe_sec(F: Fetcher) -> dict:
    a = F.get("https://data.sec.gov/submissions/CIK0000320193.json", check_robots=False, max_bytes=400_000)
    b = F.get(
        "https://efts.sec.gov/LATEST/search-index?q=%22certificate%20of%20need%22&forms=10-K&dateRange=custom&startdt=2026-01-01&enddt=2026-11-01",
        check_robots=False,
    )
    aj, bj = jbody(a) or {}, jbody(b) or {}
    recent = (aj.get("filings") or {}).get("recent", {}) if isinstance(aj, dict) else {}
    hits = ((bj.get("hits") or {}).get("total") or {}).get("value") if isinstance(bj, dict) else None
    return {
        "ok": a["status"] == 200 and b["status"] == 200,
        "requests": [req_summary(a), req_summary(b)],
        "rows_retrieved": len(recent.get("accessionNumber", [])),
        "sample_fields": sorted(aj.keys()) if isinstance(aj, dict) else [],
        "sample_record": {
            "name": aj.get("name"),
            "sic": aj.get("sic"),
            "recent_form_sample": (recent.get("form") or [])[:3],
            "recent_filing_dates": (recent.get("filingDate") or [])[:2],
        },
        "latest_record_date": (recent.get("filingDate") or [None])[0],
        "details": {
            "full_text_search_hits_for_query": hits,
            "full_text_query": '"certificate of need", 10-K, 2026-01-01..2026-11-01',
            "ua_accepted": "request succeeded with our declared research User-Agent"
            if a["status"] == 200
            else None,
        },
    }


def probe_usaspending(F: Fetcher) -> dict:
    body = json.dumps(
        {
            "filters": {
                "time_period": [{"start_date": "2026-01-01", "end_date": "2026-11-01"}],
                "place_of_performance_locations": [{"country": "USA", "state": "IL", "city": "Chicago"}],
                "award_type_codes": ["A", "B", "C", "D"],
            },
            "fields": ["Award ID", "Recipient Name", "Award Amount", "Start Date"],
            "limit": 2,
            "page": 1,
        }
    ).encode()
    r = F.get(
        "https://api.usaspending.gov/api/v2/search/spending_by_award/",
        headers={"Content-Type": "application/json"},
        data=body,
        check_robots=False,
    )
    t = r["body"].decode("utf-8", "replace")
    d = jbody(r)
    rows = d.get("results", []) if isinstance(d, dict) else []
    blocked = "blocked" in t.lower() and r["status"] != 200
    return {
        "ok": r["status"] == 200 and bool(rows),
        "requests": [req_summary(r)],
        "rows_retrieved": len(rows),
        "sample_fields": sorted(rows[0].keys()) if rows else [],
        "sample_record": rows[0] if rows else {},
        "latest_record_date": None,
        "details": {"waf_block_page": blocked, "response_text": short(text_of(t), 160) if blocked else None},
    }


def probe_lever(F: Fetcher) -> dict:
    r = F.get("https://api.lever.co/v0/postings/palantir?mode=json&limit=2", check_robots=False)
    d = jbody(r)
    rows = d if isinstance(d, list) else []
    return {
        "ok": r["status"] == 200 and bool(rows),
        "requests": [req_summary(r)],
        "rows_retrieved": len(rows),
        "sample_fields": sorted(rows[0].keys()) if rows else [],
        "sample_record": {
            k: short(rows[0].get(k)) for k in ("text", "createdAt", "workplaceType") if rows and k in rows[0]
        },
        "latest_record_date": epoch_day(int(rows[0]["createdAt"]) // 1000)
        if rows and rows[0].get("createdAt")
        else None,
        "details": {
            "note": "public ATS endpoint keyed by company slug (here a non-Chicago company only to prove the API shape); a Chicago employer list would have to come from elsewhere"
        },
    }


def probe_noaa_events(F: Fetcher) -> dict:
    r = F.get("https://www.ncei.noaa.gov/pub/data/swdi/stormevents/csvfiles/", max_bytes=2_000_000)
    t = r["body"].decode("utf-8", "replace")
    files = sorted(set(re.findall(r"StormEvents_details-ftp_v1\.0_d(\d{4})_c(\d{8})\.csv\.gz", t)))
    newest = max(files) if files else None
    return {
        "ok": r["status"] == 200 and bool(files),
        "requests": [req_summary(r)],
        "rows_retrieved": len(files),
        "sample_fields": [],
        "sample_record": {
            "newest_details_file_year": newest[0] if newest else None,
            "newest_file_compile_date": newest[1] if newest else None,
        },
        "latest_record_date": (newest[1][:4] + "-" + newest[1][4:6] + "-" + newest[1][6:])
        if newest
        else None,
        "details": {
            "years_with_details_file": f"{files[0][0]}..{files[-1][0]}" if files else None,
            "files_listed": len(files),
        },
    }


def probe_swdi(F: Fetcher) -> dict:
    r = F.get(
        "https://www.ncei.noaa.gov/swdiws/csv/nx3hail/20260801:20260830/5?bbox=-87.95,41.62,-87.50,42.05",
        max_bytes=200_000,
    )
    raw = r["body"].decode("utf-8", "replace").splitlines()
    head = next((ln for ln in raw if ln.startswith("ZTIME")), "")
    data = []
    for ln in raw[1:]:
        if not ln or ln.startswith(("summary", "count", "totalTime")):
            break
        data.append(ln)
    return {
        "ok": r["status"] == 200 and bool(data),
        "requests": [req_summary(r)],
        "rows_retrieved": len(data),
        "sample_fields": head.split(","),
        "sample_record": {"first_row": short(data[0], 120) if data else None},
        "latest_record_date": None,
        "details": {
            "query": "nx3hail, Chicago bbox, 2026-08-01..2026-08-30, limit 5 (the service returns the earliest 5 in the window)",
            "first_detection_in_window": day(data[0].split(",")[0]) if data else None,
        },
    }


def probe_rrc(F: Fetcher) -> dict:
    page = F.get(
        "https://www.rrc.texas.gov/resource-center/research/data-sets-available-for-download/",
        max_bytes=2_000_000,
    )
    html = page["body"].decode("utf-8", "replace")
    reqs = [req_summary(page)]
    titles = [
        t
        for t in (
            "Drilling Permit Master",
            "Drilling Permits Pending Approval",
            "Production Data Query Dump",
            "Statewide Production Data",
        )
        if t.lower() in html.lower()
    ]
    links = re.findall(r"https://mft\.rrc\.texas\.gov/link/[0-9a-f-]{36}", html)
    first = None
    mft_listing = {}
    if links:
        r = F.get(links[0], max_bytes=600_000)
        reqs.append(req_summary(r))
        txt = text_of(r["body"].decode("utf-8", "replace")) if r["body"] else ""
        mft_listing = {
            "status": r["status"],
            "looks_like_file_listing": "Last Modified" in txt,
            "needs_login": bool(re.search(r"(?i)password|sign in|log ?in", txt[:3000])),
        }
        first = links[0].rsplit("/", 1)[-1][:8]
    return {
        "ok": page["status"] == 200 and len(links) > 5,
        "requests": reqs,
        "rows_retrieved": len(links),
        "sample_fields": [],
        "sample_record": {"data_sets_listed_on_page": titles, "mft_share_links_on_page": len(links)},
        "latest_record_date": None,
        "details": {
            "mft_listing_probe": mft_listing,
            "first_link_prefix": first,
            "note": "downloads are served by a JSF web client (GoDrive) share page; not automated here",
        },
    }


def probe_il_epa(F: Fetcher) -> dict:
    a = F.get("https://webapps.illinois.gov/EPA/DocumentExplorer/Attributes/")
    t = text_of(a["body"].decode("utf-8", "replace")) if a["body"] else ""
    b = F.get("https://epa.illinois.gov/topics/air-quality/permits.html")
    bt = text_of(b["body"].decode("utf-8", "replace")) if b["body"] else ""
    return {
        "ok": a["status"] == 200 and b["status"] == 200,
        "requests": [req_summary(a), req_summary(b)],
        "rows_retrieved": 0,
        "sample_fields": [],
        "sample_record": {
            "document_explorer_text": short(t, 180),
            "permits_page_mentions_application_status": bool(re.search(r"(?i)status", bt)),
        },
        "latest_record_date": None,
        "details": {"note": "search web applications only; no bulk or API endpoint was found on these pages"},
    }


# fmt: off
# --------------------------------------------------------------------------------------------------
# Source catalog: static assessment (author's judgment) + a live probe per source
# --------------------------------------------------------------------------------------------------

CHI = "data.cityofchicago.org"
COOK = "datacatalog.cookcountyil.gov"
IL_EDP = "illinois-edp.data.socrata.com"
NOT_READ_CHI = "License field says 'See Terms of Use'; the chicago.gov terms page returned 403 to our client (robots.txt 403), so its text was not read."


def S(id, name, cases, url, access, auth, terms_url, terms_note, coverage, freq, effort, cost, uses, quality, verdict, why, probe, **extra):
    d = {
        "id": id, "name": name, "cases": cases, "official_url": url, "access_method": access, "auth_or_key": auth,
        "terms_url": terms_url, "terms_note": terms_note, "coverage": coverage, "update_frequency": freq,
        "ingestion_effort": effort, "cost": cost, "lead_generation_uses": uses, "signal_quality_for_brickline": quality,
        "verdict": verdict, "verdict_reason": why, "_probe": probe,
    }
    d.update(extra)
    return d


SOURCES: list[dict] = [
    # ---------------- Case 1: Certificate of Need ----------------
    S("hfsrb-project-list", "Illinois HFSRB project search listing (CON + exemption projects)", [1],
      "https://hfsrb.illinois.gov/project/project-search.html", "HTML page backed by a public JSON model endpoint (the page's own data feed)", "none",
      "https://hfsrb.illinois.gov/robots.txt", "robots.txt allows all paths for generic agents; no terms-of-use page for the data was found on the site (state-wide footer links only privacy/accessibility).",
      "Illinois-wide; project years 2011-2026 in the listing; Chicago-area projects identified only by name/city text.",
      "Whenever staff publish a project (the listing changed 2026-08-19 per its modifyDate)", "small", "free",
      "Weekly diff of new CON/exemption projects (project number, facility name, city); anchor for the PDF documents.",
      "Medium as a list (names only); high once joined to the project pages and PDFs.", "VERIFIED",
      "JSON listing retrieved with every project; contains no cost, equipment, applicant or dates.",
      lambda F: probe_hfsrb_list(F)),
    S("hfsrb-project-pages", "Illinois HFSRB per-project pages (dates, status, document links)", [1],
      "https://hfsrb.illinois.gov/project.26-032-advanced-radiation-center-of-chicago.html", "HTML (server-rendered), one page per project", "none",
      "https://hfsrb.illinois.gov/robots.txt", "Same as listing; terms not found.",
      "Same project set as the listing; dates are blank on some older or newer pages.",
      "As projects move through review", "medium", "free",
      "Received date, hearing/comment deadlines, board meeting date, and links to application, completeness letter, staff report, permit approval letter, progress reports.",
      "High: stage-by-stage dates (when populated) and the document trail.", "PARTIAL",
      "Pages and document links fetched; cost/equipment/applicant live only inside the linked PDFs.",
      lambda F: probe_hfsrb_pages(F)),
    S("hfsrb-pdf-documents", "Illinois HFSRB PDFs: State Board staff reports and permit approval letters", [1],
      "https://hfsrb.illinois.gov/project.26-032-advanced-radiation-center-of-chicago.html", "PDF documents linked from each project page (applications are scanned images)", "none",
      "https://hfsrb.illinois.gov/robots.txt", "Same as listing; terms not found.",
      "Staff reports exist for projects that reached a board meeting; approval letters for approved permits; application PDFs look like scanned images (the one application sampled by hand during exploration, 26-032, had 168 pages and no extractable text on pages 1-3; not part of the automated probe). The 26-032 staff report states the FY2026 Capital Expenditure Minimum for major medical equipment: $4,779,437.",
      "Per board meeting (monthly-ish) and per approval", "large", "free",
      "Project cost, applicant, facility address, project description (equipment named in prose), completion date: the supplier-facing facts.",
      "Highest content value (cost + equipment + dates), lowest structure.", "PARTIAL",
      "First pages of staff reports and approval letters are text PDFs with a fixed header block; applications are image-only; no PDF library is a project dependency.",
      lambda F: probe_hfsrb_docs(F)),
    S("ga-dch-con-tracking", "Georgia DCH Certificate of Need weekly tracking report (PDF)", [1],
      "https://dch.georgia.gov/divisionsoffices/office-health-planning/certificate-need-con/con-tracking-report", "Weekly PDF linked from one HTML page", "none",
      "https://dch.georgia.gov/robots.txt", "robots.txt does not disallow /document/ or this page; no data terms found. Contact names and phone numbers appear in the report (business contacts of applicants).",
      "Georgia statewide; the page holds only the current week's file; older weeks are not linked.",
      "Weekly (the 2026-11-10 file covers 2026-11-04 to 2026-11-10 and was posted by 2026-11-12)", "medium", "free",
      "Letters of intent (batching) and applications with service type, estimated cost, site and contact: a lead-time window for equipment sellers (length not measured; Georgia, not Chicago).",
      "High content, but Georgia only; history needs a self-built archive or the Wayback Machine.", "PARTIAL",
      "Current weekly PDF fetched and text-extracted (needs a PDF library); no history on the site.",
      lambda F: probe_ga_tracking(F)),
    S("cms-pos", "CMS Provider of Services file (QIES), latest quarter", [1],
      "https://data.cms.gov/provider-characteristics/hospitals-and-other-facilities/provider-of-services-file-hospital-non-hospital-facilities", "data-api JSON + CSV download on data.cms.gov", "none",
      "https://data.cms.gov/terms-of-use", "Terms page is a JavaScript app (text not extractable by plain GET); data are federal. robots.txt sets Crawl-delay: 10 (honored).",
      "National, one row per certified facility, ~470 fields incl. service flags (CT, MRI, cardiac cath, radiation therapy rooms, beds).",
      "Quarterly (latest 2026-07-01 file modified 2026-10-16)", "small", "free",
      "Installed-base context for equipment sellers: which Illinois hospitals/ASCs report CT, MRI, cath labs, OR counts; ownership changes (CHOW).",
      "Medium: capability flags, not purchase events; useful for qualification and territory sizing.", "VERIFIED",
      "Illinois rows retrieved through the documented data API.",
      lambda F: probe_cms(F, "8ba0f9b4-9493-4aa0-9f82-44ea9468d1b5", "filter[STATE_CD]=IL", ("FAC_NAME", "CITY_NAME", "STATE_CD", "ZIP_CD", "BED_CNT", "CT_SCAN_SRVC_CD", "MGNTC_RSNC_IMG_SRVC_CD", "CRTFCTN_DT"), "CT_SCAN_SRVC_CD and MGNTC_RSNC_IMG_SRVC_CD are service flags (MRI), CRDC_CTHRTZTN_PRCDR_ROOMS_CNT counts cath rooms")),
    S("cms-hospital-enrollments", "CMS Hospital Enrollments (PECOS) and Hospital All Owners, latest", [1, 4],
      "https://data.cms.gov/provider-characteristics/hospitals-and-other-facilities/hospital-enrollments", "data-api JSON + CSV on data.cms.gov", "none",
      "https://data.cms.gov/terms-of-use", "Same as above (terms text not extractable; Crawl-delay 10).",
      "National; enrollment, practice location, organization names; the 'All Owners' companion lists owners (individuals and companies).",
      "Monthly (latest 2026-10-01)", "small", "free",
      "Change of ownership and new-enrollment flags for hospitals; owner company names for B2B targeting.",
      "Low-medium for contractors; medium for healthcare-sales.", "VERIFIED",
      "Illinois enrollment rows retrieved.",
      lambda F: probe_cms(F, "f6f6505c-e8b0-4d57-b258-e2b94133aaf2", "filter[STATE]=IL", ("ENROLLMENT ID", "ORGANIZATION NAME", "CITY", "STATE", "ENROLLMENT STATE"), "owners file is a separate dataset (029c119f-...)")),
    S("cms-hcris-hospital-cost-report", "CMS Hospital Provider Cost Report (HCRIS-derived), latest fiscal year", [1],
      "https://data.cms.gov/provider-compliance/cost-report/hospital-provider-cost-report", "data-api JSON + CSV on data.cms.gov (one dataset per fiscal year)", "none",
      "https://data.cms.gov/terms-of-use", "Same as above.",
      "National, FY2011-FY2024 files (14 listed); one row per hospital cost report with beds, days, revenue and expense totals, capital cost lines.",
      "Annual (FY2024 file modified 2026-10-05)", "medium", "free",
      "Capital spending trend and size of Illinois hospitals; identifies hospitals with rising capital cost lines before they file CON projects.",
      "Medium: 1-2 year lag, hospital-level aggregates only.", "VERIFIED",
      "Latest-year rows retrieved; Illinois filter used where the dataset exposes a state column.",
      lambda F: probe_cms(F, "44060663-47d8-4ced-a115-b53b4c270acb", "filter[State Code]=IL", ("Provider CCN", "Hospital Name", "City", "State Code", "Fiscal Year End Date", "Number of Beds + Total for all Subproviders"), "raw HCRIS worksheets are also on cms.gov (not probed)")),
    S("nppes-api", "NPPES NPI Registry API (v2.1)", [1, 4],
      "https://npiregistry.cms.hhs.gov/api/", "REST JSON API", "none",
      "https://npiregistry.cms.hhs.gov/api-page", "Terms not found in the response; robots.txt has no rules. Result limits were not re-verified in this run.",
      "National, every NPI (organizations NPI-2 and individuals NPI-1) with taxonomy, addresses, phone, enumeration and last-update dates.",
      "Daily changes (API); monthly full file", "small", "free",
      "New healthcare organizations (enumeration_date) in Chicago as a new-business signal; address and phone for outreach.",
      "Medium-high for healthcare B2B (new clinics register an NPI before they open); no cost or equipment data.", "VERIFIED",
      "Chicago organizational NPIs returned.",
      lambda F: probe_nppes_api(F)),
    S("nppes-monthly-file", "NPPES monthly full file and weekly delta files", [1, 4],
      "https://download.cms.gov/nppes/NPI_Files.html", "Bulk ZIP (~1.1 GB monthly, weekly deltas, deactivation report)", "none",
      "https://download.cms.gov/nppes/NPI_Files.html", "Page lists the files; no terms text found on the page.",
      "National, full history of enumerations.", "Monthly full file; weekly update file", "medium", "free",
      "Bulk load for enumeration-date backtests (how long from NPI to first permit or license).",
      "Same as the API; better for backtests.", "VERIFIED",
      "Latest monthly ZIP exists and honors Range requests (only 200 bytes read).",
      lambda F: probe_range(F, "", "https://download.cms.gov/nppes/NPI_Files.html")),
    S("idph-hospital-directory", "Illinois IDPH Hospital Directory (Illinois open data portal)", [1],
      "https://illinois-edp.data.socrata.com/d/53nt-jwqq", "Socrata API", "none (app token optional)",
      "https://illinois-edp.data.socrata.com/api/views/53nt-jwqq.json", "See license_terms_link in the probe details.",
      "Illinois hospitals licensed by IDPH (address, license number, beds).", "Updated 2026-11-13 per portal", "small", "free",
      "Licensed facility master list to join with HFSRB project names and CMS POS.",
      "Medium: master data, not events.", "VERIFIED", "Rows retrieved via Socrata.",
      lambda F: probe_socrata(F, IL_EDP, "53nt-jwqq")),
    S("idph-astc-directory", "Illinois IDPH Ambulatory Surgical Treatment Center Directory", [1],
      "https://illinois-edp.data.socrata.com/d/79iq-26tb", "Socrata API", "none (app token optional)",
      "https://illinois-edp.data.socrata.com/api/views/79iq-26tb.json", "See license_terms_link in the probe details.",
      "Illinois ASTCs (licensed surgery centers).", "Updated 2026-11-13 per portal", "small", "free",
      "Facility master list for surgery centers (a main buyer of equipment and buildouts).", "Medium: master data.", "VERIFIED",
      "Rows retrieved via Socrata.", lambda F: probe_socrata(F, IL_EDP, "79iq-26tb")),
    S("openfda-device-registration", "openFDA device registration and listing", [1],
      "https://open.fda.gov/apis/device/registrationlisting/", "REST JSON API", "none (key optional, raises limits)",
      "https://open.fda.gov/terms/", "Terms page not fetched; the API response carries a 'do not rely on' disclaimer and says access may be restricted under its Terms of Service.",
      "Registered device establishments (makers, importers); not hospitals' installed equipment.", "Weekly (last_updated 2026-11-02 in the response meta)", "small", "free",
      "Prospect list of Illinois device makers/distributors (seller side), not demand signals from buyers.",
      "Low for Brickline's use cases: there is no public registry of installed MRI/CT units.", "PARTIAL",
      "API works for makers and importers; it is not a demand-side registry.",
      lambda F: probe_openfda(F)),

    # ---------------- Case 2: building permits / plan review ----------------
    S("seattle-building-permits", "Seattle Building Permits (SDCI), issued and in progress", [2],
      "https://data.seattle.gov/d/76t5-zqzr", "Socrata API", "none (app token optional)",
      "https://data.seattle.gov/api/views/76t5-zqzr.json", "Portal license field: Public Domain (from the dataset metadata).",
      "Seattle; includes permits applied for but not yet issued (earliest date in the data is a 1900-01-01 placeholder).", "Daily (rows updated 2026-11-15)", "small", "free",
      "Reference model for stage timing: applied, initial review complete, plan review complete, ready to issue, issued, completed; status shows where each application is.",
      "High as a method reference; not Chicago.", "VERIFIED", "Rows and stage fields retrieved.",
      lambda F: probe_socrata(F, "data.seattle.gov", "76t5-zqzr", date_field="applieddate", group_field="statuscurrent", extra_dates=("issueddate", "readytoissuedate", "planreviewcompletedate"), redact=("contractorcompanyname",))),
    S("chicago-building-permits", "Chicago Building Permits (already ingested): stage fields", [2],
      "https://data.cityofchicago.org/d/ydr8-5enu", "Socrata API", "none (app token recommended)",
      "https://data.cityofchicago.org/api/views/ydr8-5enu.json", NOT_READ_CHI,
      "City of Chicago 2006-present.", "Daily", "small (done)", "free",
      "application_start_date and issue_date give processing time; permit_status/milestone show only issued-stage values (see probe).",
      "High for relationships and timing; no pre-issue stage.", "VERIFIED", "Stage fields probed; issued permits only.",
      lambda F: probe_socrata(F, CHI, "ydr8-5enu", date_field="issue_date", group_field=("permit_status", "permit_milestone"), extra_dates=("application_start_date",), fields_of_interest=("permit_", "permit_status", "permit_milestone", "application_start_date", "issue_date", "processing_time", "permit_type", "reported_cost"))),
    S("chicago-adu-preapproval", "Chicago Additional Dwelling Unit (ADU) preapproval applications", [2],
      "https://data.cityofchicago.org/d/j4h8-ug9m", "Socrata API", "none",
      "https://data.cityofchicago.org/api/views/j4h8-ug9m.json", NOT_READ_CHI,
      "City of Chicago; preapproval step before a building permit for coach houses and basement/attic units; rows start 2026-03-31.", "Daily", "small", "free",
      "One of the few Chicago datasets that shows an application before a permit: owner address, unit type, max units allowed, status.",
      "Medium: small volume (hundreds) and owner-applicant data (names not stored here).", "VERIFIED", "Rows retrieved.",
      lambda F: probe_socrata(F, CHI, "j4h8-ug9m", date_field="submission_date", group_field="status", redact=("applicant_first_name", "applicant_last_name", "applicant_address", "property_owner_first_name", "property_owner_last_name"), fields_of_interest=("submission_date", "status", "address", "zoning", "adu_applying_for", "max_number_of_adu_allowed", "principal_building_built_year"))),
    S("chicago-doe-environmental-permits", "Chicago Department of Environment / CDPH environmental permits (air quality, demolition, etc.)", [2, 3],
      "https://data.cityofchicago.org/d/ir7v-8mc8", "Socrata API", "none",
      "https://data.cityofchicago.org/api/views/ir7v-8mc8.json", NOT_READ_CHI,
      "City of Chicago; DOE before 2012 and after April 2026, CDPH between.", "Daily", "small", "free",
      "City-level air-permit analog: permits for air-quality-sensitive work (architectural surface, demolition, boilers) with applicant names; note hold/expiry dates.",
      "Medium: narrow permit types; useful as a precursor for demolition and facade work.", "VERIFIED", "Rows retrieved.",
      lambda F: probe_socrata(F, CHI, "ir7v-8mc8", date_field="issue_date", group_field=("application_type", "status"), fields_of_interest=("application_id", "application_type", "application_subtype", "status", "issue_date", "address", "comment"))),
    S("chicago-clerk-elms", "Chicago City Clerk eLMS API (ordinances: zoning reclassifications, Planned Developments, committee referrals)", [2],
      "https://api.chicityclerkelms.chicago.gov/", "REST JSON API (Swagger UI at the root)", "none",
      "https://api.chicityclerkelms.chicago.gov/", "No terms found on the API root page (Swagger UI only).",
      "City Council legislative matters; zoning reclassification ordinances from 2015-07 (about 1,500 in the system), each with actions, sponsors, attachments.", "Live (introduced matters appear within days)", "medium", "free",
      "Zoning reclassification ordinances (title carries the street address and zoning application number) are filed months before a building permit: the earliest public trace of rezoned or Planned Development projects; applicant and plans sit in attachments.",
      "High potential for Track 2 (pre-application projects); about 1,500 matters in 11 years, so few but large; needs address parsing of titles.", "VERIFIED",
      "Zoning reclassification ordinances retrieved with addresses, status and dates; Planned Development ordinances are not separately tagged.",
      lambda F: probe_elms(F)),
    S("chicago-dob-performance-metrics", "Chicago DOB 'Time to Issue' performance-metric datasets", [2],
      "https://data.cityofchicago.org/d/4ygs-9x34", "Socrata API", "none",
      "https://data.cityofchicago.org/api/views/4ygs-9x34.json", NOT_READ_CHI,
      "Aggregate turnaround by permit program; the portal shows last update in 2014.", "Stale", "small", "free",
      "None: aggregates, no application records.", "Low", "VERIFIED",
      "Dataset exists but is stale and aggregate; confirms Chicago publishes no in-review applications.",
      lambda F: probe_socrata(F, CHI, "4ygs-9x34")),
    S("chicago-gov-planning-pages", "chicago.gov pages: Plan Commission, Zoning Board of Appeals agendas, Dept. of Buildings permit pages", [2],
      "https://www.chicago.gov/city/en/depts/dcd/supp_info/chicago_plan_commission.html", "Web pages and PDF agendas on chicago.gov", "none",
      "https://www.chicago.gov/robots.txt", "Not read: chicago.gov answered 403 to our client for robots.txt and pages, so everything on the host was treated as no-crawl.",
      "Plan Commission, ZBA and Community Development Commission agendas (Chicago).", "Per meeting", "large", "free",
      "Pre-permit agenda items (large developments, Planned Developments, variances) if the agendas could be fetched; the Council eLMS API above is the machine-readable route.",
      "Unknown: not assessable from this client.", "BLOCKED",
      "chicago.gov denies this client at the CDN (403 including robots.txt); not worked around. Retry from another network or ask the City for an access exception.",
      lambda F: probe_http(F, "https://www.chicago.gov/city/en/depts/dcd/supp_info/chicago_plan_commission.html", expect=(r"plan commission",))),

    # ---------------- Case 3: Texas air permits and Railroad Commission + Illinois analogs ----------------
    S("tceq-central-registry", "TCEQ Central Registry files on data.texas.gov (Dallas / Fort Worth)", [3],
      "https://data.texas.gov/d/t34q-qzi3", "Socrata API", "none (app token optional)",
      "https://data.texas.gov/api/views/t34q-qzi3.json", "See license_terms_link in the probe details.",
      "Regulated entities and their program IDs (air, water, waste) by TCEQ region.", "Updated 2026-11-16 per portal", "small", "free",
      "Master list of Texas regulated sites; air permits themselves are not in this dataset.", "Medium for Texas; not Chicago.", "VERIFIED", "Rows retrieved via Socrata.",
      lambda F: probe_socrata(F, "data.texas.gov", "t34q-qzi3")),
    S("tceq-air-permit-status", "TCEQ air permit status query (New Source Review, PBR, Title V)", [3],
      "https://www2.tceq.texas.gov/airperm/index.cfm", "Web query application (no bulk download or API found)", "none",
      "https://www.tceq.texas.gov/permitting/air/nav/air_status_permits.html", "Terms not found; the TCEQ download page lists raw datasets for air emissions inventories but no NSR permit file.",
      "Texas NSR and federal operating permits and applications, pending and completed.", "Not stated", "large", "free",
      "Pending NSR applications from small operators are the Texas analog of CON: months of lead time before equipment purchase.",
      "High content; query-only access means scraping a form, which is not done here.", "PARTIAL",
      "Documentation and query form are public, but the origin returned Cloudflare 522 (connection timed out) on every attempt in this session (four, spread over about an hour).",
      lambda F: probe_http(F, "http://www2.tceq.texas.gov/airperm/index.cfm", expect=(r"air|permit",))),
    S("rrc-data-downloads", "Texas Railroad Commission data sets available for download (drilling permits, production)", [3],
      "https://www.rrc.texas.gov/resource-center/research/data-sets-available-for-download/", "Bulk files (ASCII/CSV/PDF) via anonymous managed-file-transfer share pages", "none",
      "https://www.rrc.texas.gov/resource-center/research/data-sets-available-for-download/", "No terms text found on the page.",
      "Texas; drilling permit master since 1976, pending permits twice daily, production, wellbore.", "Nightly to monthly by file", "medium", "free",
      "Drilling permit applications by operator (W-1) are the Texas oil-and-gas lead event; small operators identified by operator number.",
      "High for oil and gas suppliers; irrelevant to Chicago.", "PARTIAL",
      "Page and share links verified; actual downloads go through a JSF web client and were not automated.",
      lambda F: probe_rrc(F)),
    S("rrc-well-bottom-location", "RRC well bottom location (data.texas.gov)", [3],
      "https://data.texas.gov/d/uumf-5r4y", "Socrata API", "none (app token optional)",
      "https://data.texas.gov/api/views/uumf-5r4y.json", "See license_terms_link in the probe details.",
      "Texas wells (API number, coordinates).", "Updated 2026-11-16 per portal", "small", "free",
      "Well locations; the drilling permit dataset itself was not found on data.texas.gov.", "Low-medium.", "VERIFIED", "Rows retrieved via Socrata.",
      lambda F: probe_socrata(F, "data.texas.gov", "uumf-5r4y")),
    S("il-epa-air-permits", "Illinois EPA Bureau of Air permit applications and Document Explorer", [3],
      "https://epa.illinois.gov/topics/air-quality/permits.html", "Web pages and a document-search web application", "none",
      "https://epa.illinois.gov/", "Terms not found.",
      "Illinois air construction/operating permits.", "Not stated", "large", "free",
      "Illinois analog of TCEQ NSR: permit application receipts for new emission sources (boilers, generators, paint booths).",
      "Medium-high if the application list can be obtained without form scraping.", "PARTIAL",
      "Pages reachable; no bulk file or API found, only a search application.",
      lambda F: probe_il_epa(F)),
    S("epa-echo-cook-air", "EPA ECHO facility search REST services (Cook County air-program facilities)", [3],
      "https://echo.epa.gov/tools/web-services", "REST JSON API and bulk downloads", "none",
      "https://echo.epa.gov/resources/echo-data/about-the-data", "ECHO is a federal compliance database; the about page was reachable; no explicit reuse terms matched.",
      "National facilities; here Cook County IL active facilities with a Clean Air Act program ID.", "Facility ID weekly; compliance data refreshed regularly", "small", "free",
      "Inventory of permitted industrial sources with NAICS, inspections and violations; targets for environmental and equipment services.",
      "Medium: current state only, but strong for B2B prospecting of industrial sites.", "VERIFIED", "Facility rows retrieved.",
      lambda F: probe_echo(F)),

    # ---------------- Case 4: new businesses ----------------
    S("fl-sunbiz-bulk", "Florida Division of Corporations (Sunbiz) data downloads", [4],
      "https://dos.fl.gov/sunbiz/other-services/data-downloads/", "Daily and quarterly bulk files via SFTP (credentials published on the agency page) or browser", "published public login on the agency's own page",
      "https://dos.fl.gov/sunbiz/other-services/data-downloads/", "Page says: free downloads 'for informational purposes', offered as is, may change. No other terms found. The dos.sunbiz.org copy of the page is disallowed for crawlers by robots.txt and was not fetched.",
      "Florida corporations, LLCs, partnerships, fictitious names; quarterly snapshots plus daily filings.", "Daily and quarterly", "medium", "free",
      "New-entity detection by filing date (file layout not inspected here).",
      "High for Florida; shows the model Chicago lacks (free bulk daily new-entity feed).", "PARTIAL",
      "Documentation verified; the SFTP site was not connected to (no SSH client in the standard library).",
      lambda F: probe_http(F, "https://dos.fl.gov/sunbiz/other-services/data-downloads/", expect=(r"Daily files", r"Quarterly files"))),
    S("il-sos-business-entities", "Illinois Secretary of State business entity search and bulk data", [4],
      "https://apps.ilsos.gov/corporatellc/", "Web search application (blocked to our client); whether bulk data exists could not be checked", "none for search; bulk unknown",
      "https://www.ilsos.gov/", "Not read: the host returned 403 'Access Denied' to our client, including for robots.txt.",
      "Illinois entities (corporations, LLCs, LPs).", "Live search; bulk file cadence not verified", "large", "unknown (not verified)",
      "New Illinois entities by file date; registered agents.", "High if obtainable; not obtainable here.", "BLOCKED",
      "Access denied from this client (CDN block, including robots.txt); not worked around. Bulk availability and price must be confirmed with the Secretary of State by hand.",
      lambda F: probe_http(F, "https://apps.ilsos.gov/corporatellc/", expect=(r"corporation|llc",))),
    S("chicago-business-licenses-history", "Chicago Business Licenses (full history; application type, dates, activity)", [4],
      "https://data.cityofchicago.org/d/r5kz-chrr", "Socrata API", "none (app token recommended)",
      "https://data.cityofchicago.org/api/views/r5kz-chrr.json", NOT_READ_CHI,
      "City of Chicago; all license types, one row per license term.", "Daily", "small", "free",
      "ISSUE vs RENEW vs C_LOC (change of location) application types separate new businesses from renewals; account numbers link terms; address + activity + dates.",
      "High: richest Chicago new-business feed; already partly ingested as current-active only.", "VERIFIED",
      "Full-history dataset retrieved with application types and dates.",
      lambda F: probe_socrata(F, CHI, "r5kz-chrr", date_field="date_issued", group_field=("application_type", "license_status"), extra_dates=("application_created_date",), redact=("legal_name", "address", "latitude", "longitude", "location"), fields_of_interest=("account_number", "application_type", "license_description", "business_activity", "application_created_date", "date_issued", "license_start_date", "expiration_date", "license_status", "zip_code"))),
    S("il-idfpr-professional-licensing", "Illinois IDFPR Professional Licensing (Illinois open data portal)", [4],
      "https://illinois-edp.data.socrata.com/d/pzzh-kp68", "Socrata API", "none (app token optional)",
      "https://illinois-edp.data.socrata.com/api/views/pzzh-kp68.json", "See license_terms_link in the probe details.",
      "Illinois professional licenses (individuals and some facilities).", "Updated 2026-11-16 per portal", "small", "free",
      "Original issue dates for licensed professions (e.g. dental, medical, contractors licensed by IDFPR); new-practice signal.",
      "Medium: mostly individuals; practice address often missing.", "VERIFIED", "Rows retrieved; personal fields redacted in the catalog.",
      lambda F: probe_socrata(F, IL_EDP, "pzzh-kp68", date_field="original_issue_date", group_field=("license_type", "license_status"), extra_dates=("lastmodifieddate",), redact=("first_name", "last_name", "middle", "prefix", "suffix", "title"), fields_of_interest=("license_type", "description", "license_status", "original_issue_date", "effective_date", "expiration_date", "business", "city", "zip"))),
    S("census-bfs", "Census Business Formation Statistics (BFS) monthly CSV", [4],
      "https://www.census.gov/econ/bfs/index.html", "Bulk CSV (state and national, monthly)", "none for the CSV",
      "https://www.census.gov/data/developers/about/terms-of-service.html", "API terms page read: attribution notice required for services using the API; no endorsement claims. The bulk CSV is not the API.",
      "US and states (not metros or counties); business applications, high-propensity applications, formations by NAICS sector.", "Monthly (newest month in the file: 2026-10 on 2026-11-16)", "small", "free",
      "Macro baseline for 'new business' counts; does not identify individual businesses.", "Low for lead generation; useful for normalization.", "VERIFIED",
      "CSV retrieved; Illinois present, no county or metro rows.",
      lambda F: probe_census_bfs(F)),
    S("lever-public-postings", "Public applicant-tracking-system job APIs (Lever example)", [4],
      "https://github.com/lever/postings-api", "Per-company public JSON API (Lever, Greenhouse); company slug required", "none",
      "https://github.com/lever/postings-api", "Terms for third-party aggregation not found.",
      "One company per call; no geographic search.", "Live", "large", "free",
      "Hiring signal for companies already identified (e.g. new licensed businesses with career pages).",
      "Low: no Chicago employer list is available; large job boards (Indeed, LinkedIn) were not probed (no sanctioned public API for this use was found; scraping them is out of scope).", "PARTIAL",
      "API shape verified on a non-Chicago employer; no Chicago employer list exists in the public sources probed.",
      lambda F: probe_lever(F)),

    # ---------------- Case 5: roofs ----------------
    S("orlando-permit-applications", "City of Orlando Permit Applications (open data)", [5],
      "https://data.cityoforlando.net/d/ryhf-m453", "Socrata API", "none (app token optional)",
      "https://data.cityoforlando.net/api/views/ryhf-m453.json", "See license_terms_link in the probe details.",
      "City of Orlando; applications with review stage dates through issuance and certificate dates.", "Daily", "small", "free",
      "Reference model: application status plus under-review, pending-issuance and issue dates, contractor name and estimated cost.",
      "High as a method reference; Orlando, not Chicago.", "VERIFIED", "Rows and stage dates retrieved.",
      lambda F: probe_socrata(F, "data.cityoforlando.net", "ryhf-m453", date_field="processed_date", group_field=("application_status", "application_type"), extra_dates=("under_review_date", "issue_permit_date"), redact=("property_owner_name", "parcel_owner_name", "contractor_phone_number"), fields_of_interest=("permit_number", "application_type", "worktype", "application_status", "processed_date", "issue_permit_date", "estimated_cost", "contractor_name"))),
    S("fdor-property-rolls", "Florida Dept. of Revenue assessment roll files (NAL/SDF) incl. Orange County", [5],
      "https://floridarevenue.com/property/Pages/DataPortal_RequestAssessmentRollGISData.aspx", "Bulk files per county from the state data portal", "none",
      "https://floridarevenue.com/property/Pages/DataPortal_RequestAssessmentRollGISData.aspx", "Page read; no reuse terms found.",
      "All 67 Florida counties; real property roll (NAL), sale data (SDF).", "Preliminary July, final October and after VAB", "medium", "free",
      "Roof-age proxy: year built and effective year built per parcel to pair with permits.", "Medium.", "PARTIAL",
      "Documentation page verified; file downloads were not fetched.",
      lambda F: probe_http(F, "https://floridarevenue.com/property/Pages/DataPortal_RequestAssessmentRollGISData.aspx", expect=(r"NAL", r"Sale Data File"))),
    S("orange-county-property-appraiser", "Orange County (FL) Property Appraiser web site", [5],
      "https://ocpaweb.ocpafl.org/", "Single-page web application", "none",
      "https://ocpaweb.ocpafl.org/", "Terms not found.",
      "Orange County parcels.", "Not stated", "large", "unknown",
      "Parcel records and sales by address.", "Not assessable: no data export endpoint found with plain requests.", "NOT FOUND",
      "The site is a JavaScript app (Angular) that shows 'Please enable JavaScript'; no bulk or API link was found; Florida's state portal is the practical route.",
      lambda F: probe_http(F, "https://ocpaweb.ocpafl.org/", expect=(r"download|bulk data|csv export",))),
    S("noaa-storm-events", "NOAA NCEI Storm Events Database (bulk CSV, already ingested)", [5],
      "https://www.ncei.noaa.gov/pub/data/swdi/stormevents/csvfiles/", "Bulk gzipped CSV per year (details, locations, fatalities)", "none",
      "https://www.ncei.noaa.gov/pub/data/swdi/stormevents/csvfiles/", "Directory listing only; NOAA data is federal; no terms text matched.",
      "United States, 1950-present; hail events with size at report points.", "Files recompiled monthly (newest details file compiled 2026-10-26)", "small (done)", "free",
      "Hail/wind event dates and sizes for roofing triggers; spotter points, not footprints.", "Low in Chicago (H04, H05 found no signal).", "VERIFIED",
      "Directory listing read; newest file compile date recorded.",
      lambda F: probe_noaa_events(F)),
    S("noaa-swdi-hail", "NOAA SWDI NEXRAD Level-3 hail signatures (already ingested)", [5],
      "https://www.ncei.noaa.gov/swdiws/", "REST CSV service", "none",
      "https://www.ncei.noaa.gov/swdiws/", "Service page only; no terms text matched.",
      "United States, radar-detected hail cells; the project pulls the Chicago box.", "Near real time", "small (done)", "free",
      "Hail footprints for roofing; the signal lab found no lift (H28).", "Low in Chicago.", "VERIFIED",
      "Chicago-box query returned detections.", lambda F: probe_swdi(F)),
    S("cook-assessor-residential-chars", "Cook County Assessor residential characteristics (roof construction, year built)", [5],
      "https://datacatalog.cookcountyil.gov/d/x54s-btds", "Socrata API", "none (app token optional)",
      "https://datacatalog.cookcountyil.gov/api/views/x54s-btds.json", "See license_terms_link in the probe details.",
      "Cook County single- and multi-family improvements by tax year.", "Updated 2026-11-15 per portal", "small (already ingested as res_chars)", "free",
      "char_yrblt and char_roof_cnst (roof construction code), char_repair_cnd; roof-age proxy for residential roofing.",
      "Medium: roof construction code only (no roof age or replacement year).", "VERIFIED", "Rows retrieved; roof field present.",
      lambda F: probe_socrata(F, COOK, "x54s-btds", fields_of_interest=("pin", "year", "class", "char_yrblt", "char_roof_cnst", "char_repair_cnd", "char_bldg_sf"))),
    S("cook-assessor-commercial-valuation", "Cook County Assessor commercial valuation data", [5],
      "https://datacatalog.cookcountyil.gov/d/csik-bsws", "Socrata API", "none (app token optional)",
      "https://datacatalog.cookcountyil.gov/api/views/csik-bsws.json", "See license_terms_link in the probe details.",
      "Cook County commercial and multifamily properties valued by the assessor (income-approach data).", "Updated 2025-12-30 per portal (annual)", "small", "free",
      "Building size, stories, use, owner and taxpayer, income and market value: qualifies commercial properties (no roof material field).",
      "Medium: no roof fields; annual snapshot.", "VERIFIED", "Rows retrieved; no roof column exists.",
      lambda F: probe_socrata(F, COOK, "csik-bsws", redact=("owner", "taxpayer"), fields_of_interest=("keypin", "year", "address", "bldgsf", "stories", "property_type_use", "finalmarketvalue", "class_es"))),

    # ---------------- Cross-cutting ----------------
    S("sam-opportunities-api", "SAM.gov Get Opportunities public API", [0],
      "https://open.gsa.gov/api/get-opportunities-public-api/", "REST API", "API key tied to a SAM.gov account (required)",
      "https://open.gsa.gov/api/get-opportunities-public-api/", "Documentation page read: key required, daily request limits by role.",
      "Federal solicitations nationally; filterable by place of performance.", "Live", "medium", "free (key)",
      "Federal construction/IDIQ solicitations in Illinois for subcontractor prospecting.",
      "Medium: federal work is a small share of Chicago contractor revenue.", "BLOCKED",
      "Key required; no key available to this agent. Unauthenticated calls to api.sam.gov returned an empty 404.",
      lambda F: probe_sam(F)),
    S("usaspending-api", "USAspending.gov API (awards by place of performance)", [0],
      "https://api.usaspending.gov/docs/endpoints", "REST API (POST for searches)", "none documented",
      "https://www.usaspending.gov/about", "About page reachable; no reuse terms extracted.",
      "Federal prime awards and subawards since 2008.", "Daily", "medium", "free",
      "Federal awards in Chicago with recipient names; incumbent contractors and subaward partners.", "Medium.", "BLOCKED",
      "Every request from this client was answered by a web-application-firewall block page (HTTP 500); not worked around. Retry from another network.",
      lambda F: probe_usaspending(F)),
    S("sec-edgar", "SEC EDGAR submissions API and full-text search", [0],
      "https://www.sec.gov/search-filings/edgar-application-programming-interfaces", "REST JSON APIs (data.sec.gov, efts.sec.gov)", "none; declared User-Agent required",
      "https://www.sec.gov/os/accessing-edgar-data", "Read: fair-access limit 10 requests/second; declare a User-Agent with contact details (name and email).",
      "All SEC filers; the full-text query returned hits for 2026 filings.", "Real time", "medium", "free",
      "Capex disclosures and facility plans of public companies with Chicago operations; low volume for small contractors.", "Low-medium.", "VERIFIED",
      "Both endpoints answered with our declared research User-Agent; the founder's contact email should be added before volume use.",
      lambda F: probe_sec(F)),
    S("census-cbp", "Census County Business Patterns (bulk county file)", [0],
      "https://www.census.gov/programs-surveys/cbp.html", "Bulk ZIP per year; API needs a key", "none for bulk; key for API (the unkeyed API call returned 'Missing Key')",
      "https://www.census.gov/data/developers/about/terms-of-service.html", "API terms read (attribution required). Bulk files: terms not found.",
      "County x NAICS, establishments by employee-size class, to 2023.", "Annual (2023 file on the site 2026-11-16)", "small", "free",
      "Market sizing: establishments per NAICS in Cook County for TAM and normalization.", "Low for leads.", "VERIFIED",
      "2023 county file present; unkeyed API call failed.",
      lambda F: probe_range(F, "https://www2.census.gov/programs-surveys/cbp/datasets/2023/cbp23co.zip")),
    S("fmcsa-company-census", "FMCSA Company Census File (data.transportation.gov)", [0],
      "https://data.transportation.gov/d/az4n-8mr2", "Socrata API", "none (app token optional)",
      "https://data.transportation.gov/api/views/az4n-8mr2.json", "See license_terms_link in the probe details; the dot.gov data page is disallowed to our client (robots 403) and was not read.",
      "US motor carriers; Chicago carriers filtered by physical city.", "Daily snapshot", "small", "free",
      "Trucking/fleet prospects: power units, drivers, add_date (new carrier) and mcs150_date (last MCS-150 update); fleet-service and equipment sellers.",
      "Medium-high for fleet B2B; current state only (no change history).", "VERIFIED", "Chicago carriers retrieved.",
      lambda F: probe_socrata(F, "data.transportation.gov", "az4n-8mr2", where="phy_city='CHICAGO' AND phy_state='IL'", date_field="add_date", extra_dates=("mcs150_date",), redact=("company_officer_1", "company_officer_2", "phone", "fax", "cell_phone", "email_address"), fields_of_interest=("dot_number", "legal_name", "phy_city", "phy_zip", "power_units", "total_drivers", "add_date", "mcs150_date", "status_code"))),
    S("chicago-contracts", "City of Chicago Contracts (data portal)", [0],
      "https://data.cityofchicago.org/d/rsxa-ify5", "Socrata API", "none",
      "https://data.cityofchicago.org/api/views/rsxa-ify5.json", NOT_READ_CHI,
      "City of Chicago contracts and amendments with vendors and amounts.", "Updated 2026-11-16 per portal", "small", "free",
      "Incumbent vendors, award values, and expiring contracts for rebid timing.", "Medium-high for public-work subcontractors.", "VERIFIED", "Rows retrieved.",
      lambda F: probe_socrata(F, CHI, "rsxa-ify5", fields_of_interest=("purchase_order_description", "department", "contract_type", "award_amount", "start_date", "end_date", "vendor_name"))),
    S("cook-procurement-awards", "Cook County Procurement: awarded contracts and amendments", [0],
      "https://datacatalog.cookcountyil.gov/d/qh8j-6k63", "Socrata API", "none (app token optional)",
      "https://datacatalog.cookcountyil.gov/api/views/qh8j-6k63.json", "See license_terms_link in the probe details.",
      "Cook County Government contracts.", "Updated 2026-10-16 per portal", "small", "free",
      "Awarded contractors and amounts for county work.", "Medium.", "VERIFIED", "Rows retrieved.",
      lambda F: probe_socrata(F, COOK, "qh8j-6k63")),
    S("cook-procurement-bids", "Cook County Procurement: bid tabulations", [0],
      "https://datacatalog.cookcountyil.gov/d/32au-zaqn", "Socrata API", "none (app token optional)",
      "https://datacatalog.cookcountyil.gov/api/views/32au-zaqn.json", "See license_terms_link in the probe details.",
      "Cook County bids with bidder names and prices.", "Updated 2026-11-10 per portal", "small", "free",
      "Who bids and at what price: competitor and GC intelligence for county work.", "Medium-high for public-work subs.", "VERIFIED", "Rows retrieved.",
      lambda F: probe_socrata(F, COOK, "32au-zaqn")),
    S("cook-procurement-buying-plan", "Cook County Procurement: Buying Plan FY2026 (forward-looking)", [0],
      "https://datacatalog.cookcountyil.gov/d/cbhc-xvrm", "Socrata API", "none (app token optional)",
      "https://datacatalog.cookcountyil.gov/api/views/cbhc-xvrm.json", "See license_terms_link in the probe details.",
      "County planned procurements for the fiscal year.", "Updated 2026-02-13 per portal (one dataset per fiscal year)", "small", "free",
      "Forward-looking list of planned solicitations: the closest thing to a pre-bid pipeline in the public data.", "Medium.", "VERIFIED", "Rows retrieved.",
      lambda F: probe_socrata(F, COOK, "cbhc-xvrm")),
    S("il-future-solicitations", "State of Illinois Future Solicitations (open data portal)", [0],
      "https://illinois-edp.data.socrata.com/d/6rb8-ntpm", "Socrata API", "none (app token optional)",
      "https://illinois-edp.data.socrata.com/api/views/6rb8-ntpm.json", "See license_terms_link in the probe details.",
      "State agencies' planned solicitations.", "Updated 2026-11-16 per portal", "small", "free",
      "Forward-looking state bids (including construction through agencies), earlier than posted bids.", "Medium.", "VERIFIED", "Rows retrieved.",
      lambda F: probe_socrata(F, IL_EDP, "6rb8-ntpm")),
    S("il-cdb-registered-vendors", "Illinois Capital Development Board registered vendors", [0, 4],
      "https://illinois-edp.data.socrata.com/d/3dh9-yktq", "Socrata API", "none (app token optional)",
      "https://illinois-edp.data.socrata.com/api/views/3dh9-yktq.json", "See license_terms_link in the probe details.",
      "Contractors, architects and engineers registered for state capital projects.", "Updated 2026-11-16 per portal", "small", "free",
      "Prospect list and trade categories for contractors that chase state work.", "Medium for prospecting.", "VERIFIED", "Rows retrieved; business contact fields redacted in the catalog.",
      lambda F: probe_socrata(F, IL_EDP, "3dh9-yktq", redact=("contact_name", "email", "phone", "contact_email", "contact_phone"))),
    S("chicago-food-inspections", "Chicago Food Inspections (already ingested): freshness", [0],
      "https://data.cityofchicago.org/d/4ijn-s7e5", "Socrata API", "none",
      "https://data.cityofchicago.org/api/views/4ijn-s7e5.json", NOT_READ_CHI,
      "City of Chicago 2010-present.", "Daily", "small (done)", "free",
      "License inspections precede opening; Out of Business closure signal (H26).", "High (backtested).", "VERIFIED", "Newest inspection date recorded.",
      lambda F: probe_socrata(F, CHI, "4ijn-s7e5", date_field="inspection_date", group_field="results")),
    S("chicago-311", "Chicago 311 Service Requests (already ingested): freshness", [0],
      "https://data.cityofchicago.org/d/v6vf-nfxy", "Socrata API", "none",
      "https://data.cityofchicago.org/api/views/v6vf-nfxy.json", NOT_READ_CHI,
      "City of Chicago 2018-present.", "Daily", "small (done)", "free",
      "Building complaint, porch inspection and vacant property signals (H07-H09).", "High (backtested).", "VERIFIED", "Newest created date recorded.",
      lambda F: probe_socrata(F, CHI, "v6vf-nfxy", date_field="created_date", group_field="sr_type", redact=("street_address", "latitude", "longitude", "location", "x_coordinate", "y_coordinate"))),
]


# fmt: on


def probe_openfda(F: Fetcher) -> dict:
    r = F.get(
        "https://api.fda.gov/device/registrationlisting.json?search=registration.state_code:%22IL%22&limit=1",
        check_robots=False,
    )
    d = jbody(r) or {}
    res = d.get("results", []) if isinstance(d, dict) else []
    meta = (d.get("meta") or {}) if isinstance(d, dict) else {}
    reg = (res[0].get("registration") or {}) if res else {}
    return {
        "ok": r["status"] == 200 and bool(res),
        "requests": [req_summary(r)],
        "rows_retrieved": len(res),
        "total_records": (meta.get("results") or {}).get("total"),
        "sample_fields": sorted(res[0].keys()) if res else [],
        "sample_record": {
            "registration_fields": sorted(reg.keys())[:14],
            "establishment_type": short(res[0].get("establishment_type")) if res else None,
        },
        "latest_record_date": day(meta.get("last_updated")),
        "details": {"note": "total = Illinois registration/listing rows (makers, importers, distributors)"},
    }


def probe_sam(F: Fetcher) -> dict:
    docs = F.get("https://open.gsa.gov/api/get-opportunities-public-api/", max_bytes=1_000_000)
    txt = text_of(docs["body"].decode("utf-8", "replace")) if docs["body"] else ""
    key_required = bool(re.search(r"must provide an API key", txt))
    api = F.get("https://api.sam.gov/opportunities/v2/search?limit=1", check_robots=False)
    return {
        "ok": False,
        "requests": [req_summary(docs), req_summary(api)],
        "rows_retrieved": 0,
        "sample_fields": [],
        "sample_record": {},
        "latest_record_date": None,
        "details": {
            "docs_say_api_key_required": key_required,
            "unauthenticated_api_status": api["status"],
            "unauthenticated_api_body_bytes": api["bytes"],
        },
    }


# --------------------------------------------------------------------------------------------------
# Assessment text that depends on reading the probe results (kept with the script so the report is reproducible)
# --------------------------------------------------------------------------------------------------

RANKING: list[dict] = [
    {
        "rank": 1,
        "source": "chicago-business-licenses-history",
        "why": "Already in our warehouse as the current-active file only. The full history (1.21 million license terms since 2002-01-02) separates ISSUE (271,166) from RENEW (921,838) and change-of-location (C_LOC, 16,443) applications, with application-created and issue dates. That is the one free Chicago feed that shows a new business before it opens, and the food-license backtest (restaurant build-out about 90 days ahead of the license) shows the method works.",
        "effort": "small (same Socrata exporter, one new table)",
        "first_test": "ISSUE-type license -> renovation permit or sign permit at the address within 365 days vs the same address's own earlier window; split by business activity.",
    },
    {
        "rank": 2,
        "source": "chicago-clerk-elms",
        "why": "Zoning reclassification ordinances (1,487 since 2015-07, address and zoning application number in the title) are filed in Council months before a permit exists. This is the only machine-readable pre-permit trail for large Chicago projects that was reachable; the City's Plan Commission and ZBA web pages were not reachable from our client.",
        "effort": "medium (parse addresses from titles, join to permits by address/PIN)",
        "first_test": "Reclassification introduced -> new-construction or renovation permit >= $100k at the address; measure lead time vs permit issue date.",
    },
    {
        "rank": 3,
        "source": "hfsrb-project-list + hfsrb-project-pages (engine/collect/hfsrb.py)",
        "why": "The Chicago-area analog of the Georgia case: 1,692 projects listed 2011-2026, staff reports and permit approval letters carry project cost, facility, city, permit holders and a description that names equipment. Volume is small (about 100 projects a year statewide) but costs in the sample run from $0.25 million to $645 million; buyers would be medical-equipment sellers and healthcare GCs, which we have no customer for yet. Needs one PDF library if cost is wanted.",
        "effort": "small for the CSV (done); medium to productize PDF header extraction",
        "first_test": "Approved permits -> subcontractor/equipment-related permits at the facility address in the following 2 years (join approval letters to Chicago permits by address).",
    },
    {
        "rank": 4,
        "source": "cook-procurement-buying-plan + cook-procurement-bids + cook-procurement-awards + chicago-contracts",
        "why": "The only forward-looking public-work pipeline found in the data: Cook County's Buying Plan (planned solicitations), then bid tabulations (who bid, what price), then awards; Chicago contracts add 189,023 vendor contracts. Directly feeds Track 2 (GC open-door scores, subcontractor intelligence) and costs nothing.",
        "effort": "small (Socrata)",
        "first_test": "Buying-plan item -> posted bid -> award; check lead time and whether bidders are repeat winners (relationship graph).",
    },
    {
        "rank": 5,
        "source": "fmcsa-company-census",
        "why": "20,715 FMCSA-registered carriers with a Chicago physical address, with power units, drivers, add_date (new carriers) and MCS-150 update date. A clean, current B2B list for fleet-service sellers; a separate market from contractors, so rank depends on the founder's buyer choice.",
        "effort": "small",
        "first_test": "New carriers (add_date in last 90 days) with power_units >= 5 as a weekly list; no backtest possible (no history).",
    },
    {
        "rank": 6,
        "source": "chicago-doe-environmental-permits + epa-echo-cook-air",
        "why": "Chicago's own air-permit analog of TCEQ: 67,886 City environmental permits (29,805 'AIR POLLUTION CONTROL PERMIT') plus 4,845 active Cook County air-program facilities in EPA ECHO. Useful as an industrial-site master list and a trigger for boiler/generator/spray-booth service; the Illinois EPA permit application list itself is only a search application.",
        "effort": "small (both are APIs)",
        "first_test": "New air-pollution-control permit -> mechanical/electrical permit at the address; ECHO NAICS to find industrial prospects.",
    },
    {
        "rank": 7,
        "source": "il-idfpr-professional-licensing + idph directories + nppes-api",
        "why": "Healthcare and professional new-practice detection: IDFPR licenses (4.46 million rows with original issue dates; ODbL licence needs attribution and share-alike for derived databases), IDPH hospital/ASTC/dialysis directories (207 hospitals, 156 ASTCs), and NPPES enumeration dates. Medium signal for build-out and equipment sellers; mostly individuals, so match by practice address only.",
        "effort": "medium (entity matching to addresses)",
        "first_test": "New organizational NPI or dental/medical license with a Chicago practice address -> build-out permit within 180 days.",
    },
    {
        "rank": 8,
        "source": "chicago-adu-preapproval",
        "why": "616 ADU preapproval applications since 2026-03-31, the only Chicago application-stage permit data found; too small and too new to backtest, but it is a real pre-permit feed for residential GCs and is trivial to ingest.",
        "effort": "small",
        "first_test": "Pre-certified ADU application -> building permit at the address; wait for 12 months of history.",
    },
]

IMPLICATIONS_MD = (
    """## What this means for Brickline

**The Chicago-focused answer to each case study**

| Case | What the original source does | Chicago / Illinois equivalent found | Verdict |
| --- | --- | --- | --- |
| 1. Georgia CON -> medical equipment | Weekly PDF lists letters of intent and applications with applicant, service, site, contact and estimated cost (the brief's 6-12 month lead-time premise was not measured here) | Illinois HFSRB lists every CON and exemption project (1,692 since 2011) with a per-project page; staff reports and permit approval letters carry cost, facility, permit holders and an equipment description. No weekly report and no API, but better history than Georgia. Equipment is only named in the description text, and the equipment threshold is high (FY2026 capital expenditure minimum $4,779,437, stated in the 26-032 staff report), so typical MRI/CT replacements below it never appear. | PARTIAL, usable |
| 2. Seattle permits/plan review -> trades | Seattle publishes applications, review-complete and ready-to-issue dates, and status for 194,311 permits | Chicago publishes only issued permits (`permit_status` holds ACTIVE/COMPLETE/EXPIRED...; no in-review values) but with `application_start_date` and `issue_date`, so the review duration is known after the fact. Pre-issue Chicago traces: Council zoning reclassifications (1,487), ADU preapprovals (616). Plan Commission/ZBA agendas on chicago.gov were not reachable. | PARTIAL: stage timing only at issue |
| 3. TCEQ/RRC -> oil and gas equipment | Pending air permits and drilling permits from small operators | Chicago DOE/CDPH environmental permits (67,886) and EPA ECHO (4,845 Cook County air-program facilities) are open; Illinois EPA air permit applications are a search application only. Texas sources themselves: RRC bulk files are public but served through a JSF download client; TCEQ's air permit status page is a query app that timed out (HTTP 522). | PARTIAL |
| 4. New businesses -> buyers | Florida Sunbiz free daily/quarterly bulk files | Chicago Business Licenses full history (1.21 million terms, ISSUE vs RENEW vs C_LOC) is the strong equivalent and is free. Illinois Secretary of State entity data could not be reached from our client (403, even for robots.txt). IDFPR licenses (4.46 million) are open under ODbL. | VERIFIED (city), BLOCKED (state entities) |
| 5. Orlando roofs + appraiser + storms | Permit applications with review stages, parcel data, storm data | Cook County residential characteristics carry year built and roof construction (not roof age), Chicago permits carry prior re-roof history, and the signal lab already found no storm signal (H04/H05/H28). Orange County's appraiser site is a script-only app; Florida's state roll files are documented. | VERIFIED data, weak expected lift |

**Three findings that change plans**

1. **Chicago's biggest early-signal gap is real but partly fillable.** The permit dataset has 853,111 issued permits and no review-stage rows. The two earlier traces we can actually fetch are the Council eLMS API (zoning, about 1,500 matters in 11 years) and the business-license history. Everything else early (Plan Commission, ZBA, Department of Buildings pages) sits on chicago.gov, which refuses our client.
2. **Several useful hosts block this cloud client** (chicago.gov, ilsos.gov, api.usaspending.gov, transportation.gov pages). They were not worked around. The founder's own network may not be blocked; retest there before concluding anything about those sources.
3. **Two sources need a key or a human step:** SAM.gov (API key tied to an account) and Illinois SOS bulk data (availability unknown). Neither is worth it before the cheaper ones above.

### Ranked: ingest next for Chicago

"""
    + "\n".join(
        f"{r['rank']}. **{r['source']}**: {r['why']} Effort: {r['effort']}. First test: {r['first_test']}"
        for r in RANKING
    )
    + """

**Not worth ingesting for Chicago:** Seattle and Orlando permits (method references only: stage-duration modelling), Georgia DCH and Texas sources (wrong state), Orange County appraiser (no usable endpoint), SEC EDGAR (large companies only, though the API works with our User-Agent), Census BFS and CBP (state/county aggregates, useful only to normalize counts), job-posting APIs (no Chicago employer list), SAM.gov and USAspending (blocked by key and WAF respectively; federal work is a small share).
"""
)


FINDINGS_MD_EXTRA = """## Proof of concept: Illinois HFSRB projects (Chicago analog of Case 1)

**Result: yes, Illinois project data can be retrieved for Chicago-area projects, with cost and equipment text for most non-exempt projects.** `engine/collect/hfsrb.py` fetches it politely (User-Agent `BricklineResearchBot/0.1`, robots.txt checked, 1 request/second) into `data/raw/hfsrb/` and writes `data/hfsrb-projects.csv` (deterministic: two runs gave the same md5; sorted by project number).

Where each field comes from (all verified in this run):

| Field | Source | Structured? |
| --- | --- | --- |
| project number, project name, year, status (Exempted / Non-Exempted), deemed-complete flag | listing JSON (one request, 1,692 rows) | yes |
| received date, hearing-request and comment deadlines, board meeting date, document links | per-project HTML page | yes where the page is filled in (185 of 505 pages fetched had a received date) |
| project cost, facility, city, address, permit holders, description (equipment named in prose), completion date | first page of the State Board staff report or the permit approval letter (PDF) | text PDFs with a fixed header; needs a PDF library (`pypdf`, not a project dependency; the collector skips this step if it is missing) |
| application contents | scanned application PDF | no (image-only on the sample) |

Counts from the run `--since 2022 --documents` (pages for 2022-2026, 505 project pages, 405 PDFs):

- Listing: 1,692 projects, project years 2011-2026 (one 2010 entry): 86-154 projects a year in 2012-2026 (2026 so far: 99); 233 names mention Chicago; 1,652 have a project number (the other 40 are mostly temporary-suspension notices).
- Page-level (505 project pages, 2022-2026): 445 application links, 182 staff-report links, 350 approval-letter links.
- Document-level (2022-2026): 195 projects with a project cost, 190 with a city, 198 with a description, 153 with permit holders, 36 with an equipment keyword (dialysis 19, cath lab 7, operating rooms 5, linear accelerator 3, MRI 2, CT 2). 193 of 244 non-exempt 2022-2026 projects (79%) have a cost; exemption (E-) approval letters carry no cost, so only 2 of 221 exemption projects do.
- Chicago-city projects with documents 2022-2026: 37 (27 with a non-zero cost, $2.95 billion in total); 17 of them are 2025 or later.
- How far back: the listing reaches 2011; project pages with application, staff report and approval letter links were seen for 2012, 2014, 2016, 2018, 2020 and 2022 projects; a 2015 staff report has the same header block as a 2026 one (checked on 14-061). PDFs were only bulk-read for 2022 onward.

Ten sample rows (Chicago city, 2025 or later, non-zero cost; from `data/hfsrb-projects.csv`):

| Project | Facility | Cost | Completion | Source doc | Equipment keywords |
| --- | --- | --- | --- | --- | --- |
| 25-003 | Advocate Trinity Hospital | $319,557,882 | n/a | staff report | none |
| 25-009 | TARGET Health Cooperative Medical Clinics | $34,190,180 | n/a | staff report | none |
| 25-017 | Shirley Ryan AbilityLab | $21,284,207 | n/a | staff report | none |
| 25-019 | Six Corners Same Day Surgery Center | $5,205,709 | July 1, 2026 | approval letter | none |
| 25-025 | Northwestern Memorial Hospital (master design) | $56,242,369 | September 30, 2027 | approval letter | none |
| 25-030 | Northwestern Memorial Hospital | $95,507,133 | n/a | approval letter | dialysis |
| 25-042 | University of Illinois Medical Center (ambulatory care building) | $208,455,373 | January 31, 2026 | approval letter | none |
| 25-050 | Mount Sinai Hospital Medical Center of Chicago | $250,000 | December 31, 2026 | approval letter | none |
| 26-003 | Northwestern Memorial Hospital (demolition) | $51,283,483 | July 31, 2026 | approval letter | none |
| 26-005 | Northwestern Memorial Hospital (surgical services) | $264,935,160 | June 30, 2028 | approval letter | none |

**Extraction accuracy (hand check against the source documents).** Two checks of 10 rows each. (1) Ten Chicago-city rows (every second or third of 23 candidates), read against the PDF first pages: cost, facility, city, description and completion date matched on 10 of 10 once the two blank cities were fixed; those two had a blank city because the approval-letter layout says 'Applicants:' instead of 'Permit Holders:' (fixed afterwards). (2) Every 38th document row of the final CSV: on the 6 non-exempt rows, cost, facility and completion date matched 6 of 6, city matched 5 of 6 (O'Fallon was read as 'Illinois' because of the curly apostrophe; fixed and re-run), and the 4 exemption rows returned blanks, which is correct because their letters hold no cost. Dates read from project pages were compared on 5 rows (received date 4 of 4 where present, meeting date 1 of 1). One source-side error was found by cross-checking: the HFSRB page for 23-023 (Rush North and Harlem MOB) links the permit letter of 22-023 (Lurie iMRI, $27,741,365). The collector now compares the project number inside each PDF with the row and leaves the fields blank on a mismatch (4 of the 389 rows with a document were mismatches). The equipment flags are keyword hits on the description, not a validated classification, and a $0 permit amount means a discontinuation, not a free project.

**Caveats.** (a) Illinois only reviews projects above statutory thresholds (the 26-032 staff report states a FY2026 capital expenditure minimum of $4,779,437 for major medical equipment), so most routine MRI/CT purchases never appear. (b) Names in the listing contain typos ('26-0321', 'Washington Lag'), and the project number from the link is used when the two disagree. (c) Pages for the newest projects are often blank for dates until staff fill them in. (d) 'name_mentions_chicago' is a name match; the city from the PDF (`doc_city`) is more reliable and covers only projects with documents.

## Quick feasibility: Georgia DCH weekly CON report

Verified. The page lists one PDF per week (`/document/report/11-10-2026-tracking-report/download`, 710,843 bytes, 32 pages, report period 2026-11-04 to 2026-11-10, file last modified 2026-11-12). With `pypdf` the text extracts cleanly in a regular layout: 2 letters of intent (each with received date and 'application must be submitted on' date) and 18 distinct application IDs across sections (applicant, service or project type, filed, deemed-complete and decision-deadline dates, site with county, contact name and phone; 9 'Estimated Cost' lines totalling $149.3 million). The current report has 5 pending-review applications, including MegaVoltage radiation therapy establishments and expansions ($13.87 and $6.99 million among them), none recently approved, and two recently denied 'Replacement of (Existing) MRI and CT Scanner(s)' applications ($3.9 million, denied 2026-10-23, opposition filed): exactly the equipment-demand signal described in the brief. Limits: only the current week is linked (the Wayback Machine CDX index returned no captures for the URL pattern), so history needs our own weekly archive; no API or CSV; no terms or reuse language was found on the pages read.

## Chicago stage fields for Case 2 (what the existing permit dataset can and cannot say)

`ydr8-5enu` has `application_start_date` (newest 2026-11-15) and `issue_date` (newest 2026-11-15), `processing_time`, `permit_status` and `permit_milestone`. Status values (counts): COMPLETE 487,036, ACTIVE 31,200, EXPIRED 16,877, SUSPENDED 13,248, PHASED PERMITTING 975, CANCELLED 401, REVOKED 292, null 303,082; milestones are post-issue (INSPECTIONS, CERTIFICATE OF OCCUPANCY ISSUED, INSPECTION ELIGIBLE, 'PERMIT ISSUED (FEE DUE)' 672). There are no in-review values, so Chicago does not publish applications before issue in this dataset; Seattle's equivalent (`76t5-zqzr`) has 12+ in-progress statuses (Additional Info Requested 10,336, Reviews In Process 562, Ready for Issuance 697) plus initial-review, plan-review-complete and ready-to-issue dates, and Orlando's (`ryhf-m453`) has under-review and pending-issuance dates. The nearest Chicago traces are the Council zoning reclassification API (1,487 matters since 2015-07) and ADU preapproval applications (616 since 2026-03-31).
"""


def run_source(F: Fetcher, spec: dict) -> dict:
    out = {k: v for k, v in spec.items() if not k.startswith("_")}
    try:
        probe = spec["_probe"](F)
    except Exception as exc:  # a probe bug must not hide the other sources
        probe = {
            "ok": False,
            "requests": [],
            "details": {"probe_exception": f"{type(exc).__name__}: {exc}"[:300]},
        }
    pages = probe.pop("_pages", None)
    probe = strip_private(probe)
    out["probe"] = probe
    if spec["verdict"] == "VERIFIED" and not probe.get("ok"):
        out["verdict"] = "UNVERIFIED (probe failed this run)"
    elif spec["verdict"] in ("BLOCKED", "NOT FOUND") and probe.get("ok"):
        out["verdict_reason"] += " NOTE: the probe succeeded this run; re-assess."
    del pages
    return out


def table(rows: list[list[str]], header: list[str]) -> str:
    lines = ["| " + " | ".join(header) + " |", "| " + " | ".join("---" for _ in header) + " |"]
    for r in rows:
        lines.append("| " + " | ".join(str(c).replace("|", "/").replace("\n", " ") for c in r) + " |")
    return "\n".join(lines)


def fmt(v) -> str:
    if v is None:
        return "n/a"
    if isinstance(v, int):
        return f"{v:,}"
    return str(v)


def short_text(text: str, n: int) -> str:
    text = text.strip()
    return text if len(text) <= n else text[: n - 3].rsplit(" ", 1)[0] + "..."


def short_access(text: str) -> str:
    first = re.split(r";| \(| via ", text)[0].strip()
    return first if len(first) <= 70 else first[:67].rsplit(" ", 1)[0] + "..."


def render_md(doc: dict) -> str:
    srcs = doc["sources"]
    out = [f"# Source verification, {doc['run_date']} (Deliverable A)", ""]
    out.append(
        "Every source below was requested with a descriptive User-Agent "
        f"(`{doc['user_agent']}`), robots.txt checked first, at most one request per second per host (robots Crawl-delay honored), "
        "and only small samples (Socrata `$limit=5`, capped downloads, HTTP Range for bulk files). Nothing was bypassed: "
        "blocked requests are recorded as blocked. 'Verified' means the data was actually retrieved in this run; "
        "'partial' means documents/portal only or only part of the chain was retrieved. In the JSON, the `probe` object of "
        "each source holds what was measured; every other field (coverage, effort, signal quality, uses, verdict reason) is the "
        "author's assessment, written from the probe results and the pages read."
    )
    out += [
        "",
        "Machine-readable catalog: `research/findings/source-verification-2026-11-16.json` (regenerate with `python3 research/probes/source_check.py`).",
        "",
    ]
    out += ["## Summary table", ""]
    rows = []
    for s in srcs:
        p = s["probe"]
        rows.append(
            [
                f"`{s['id']}`",
                s["name"],
                ",".join(str(c) for c in s["cases"]),
                s["verdict"],
                short_access(s["access_method"]),
                s["cost"],
                fmt(
                    p.get("total_records") if p.get("total_records") is not None else p.get("rows_retrieved")
                ),
                short_text(s["signal_quality_for_brickline"], 95),
            ]
        )
    out.append(
        table(
            rows,
            [
                "Source",
                "Name",
                "Case",
                "Verdict",
                "Access",
                "Cost",
                "Records seen",
                "Signal quality for Brickline",
            ],
        )
    )
    out += [
        "",
        "Case 0 = cross-cutting. 'Records seen' is the dataset total where the API reports one, otherwise the sample size retrieved.",
        "",
    ]
    out.append(IMPLICATIONS_MD.strip())
    out += ["", FINDINGS_MD_EXTRA.strip(), "", "## Catalog (one entry per source)", ""]
    for s in srcs:
        p = s["probe"]
        out.append(f"### `{s['id']}`: {s['name']}")
        out.append("")
        out.append(f"- **Verdict: {s['verdict']}.** {s['verdict_reason']}")
        out.append(f"- Official URL: {s['official_url']}")
        out.append(
            f"- Access method: {s['access_method']}. Auth or key: {s['auth_or_key']}. Cost: {s['cost']}."
        )
        reqs = p.get("requests", [])
        st = ", ".join(f"{r.get('status')}" for r in reqs) or "none"
        errs = [r["error"] for r in reqs if r.get("error")]
        probe_line = f"- Probe: {len(reqs)} request(s), HTTP status {st}"
        if p.get("rows_retrieved") is not None:
            probe_line += f"; {fmt(p.get('rows_retrieved'))} sample rows/records retrieved"
        if p.get("total_records") is not None:
            probe_line += f"; dataset total {fmt(p['total_records'])}"
        if p.get("latest_record_date"):
            probe_line += f"; newest record date {p['latest_record_date']}"
        det = p.get("details", {})
        if det.get("earliest_record_date"):
            probe_line += f"; earliest {det['earliest_record_date']}"
        if det.get("rows_updated_at"):
            probe_line += f"; portal rows-updated {det['rows_updated_at']}"
        out.append(probe_line + ".")
        if errs:
            out.append(f"- Probe errors: {'; '.join(errs)}")
        if p.get("sample_fields"):
            fl = p["sample_fields"]
            out.append(
                f"- Sample fields ({len(fl)}): "
                + ", ".join(f"`{f}`" for f in fl[:24])
                + (" ..." if len(fl) > 24 else "")
            )
        extra = {
            k: v
            for k, v in det.items()
            if k
            not in (
                "rows_updated_at",
                "earliest_record_date",
                "description",
                "documents",
                "searches",
                "dataset_name",
            )
            and v not in (None, {}, [])
        }
        if det.get("dataset_name"):
            out.append(
                f"- Portal name: {det['dataset_name']}"
                + (f"; license: {det['license']}" if det.get("license") else "")
                + (f"; terms link: {det['license_terms_link']}" if det.get("license_terms_link") else "")
            )
        if extra:
            out.append(
                "- Probe details: `"
                + json.dumps(
                    {
                        k: v
                        for k, v in extra.items()
                        if k not in ("license", "license_terms_link", "attribution")
                    },
                    sort_keys=True,
                )[:700]
                + "`"
            )
        out.append(f"- Coverage: {s['coverage']} Update frequency: {s['update_frequency']}.")
        out.append(f"- Terms: {s['terms_url']} ({s['terms_note']})")
        out.append(
            f"- Ingestion effort: {s['ingestion_effort']}. Lead uses: {s['lead_generation_uses']} Signal quality: {s['signal_quality_for_brickline']}"
        )
        out.append("")
    return "\n".join(out) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--only", nargs="*", help="source ids to probe (writes *.partial.* files)")
    ap.add_argument("--fetch", help="one polite GET for exploration")
    ap.add_argument(
        "--merge",
        action="store_true",
        help="with --only: replace those sources inside the full findings file",
    )
    ap.add_argument("--render", help="re-render the .md next to an existing findings .json (no requests)")
    ap.add_argument("--date", default=RUN_DATE)
    ap.add_argument("--out", default=str(ROOT / "research" / "findings"))
    a = ap.parse_args()
    if a.render:
        path = Path(a.render)
        path.with_suffix(".md").write_text(render_md(json.loads(path.read_text())))
        print(f"re-rendered {path.with_suffix('.md')}", file=sys.stderr)
        return 0
    F = Fetcher()
    if a.fetch:
        r = F.get(a.fetch)
        print(r["status"], r["content_type"], r["bytes"], r.get("error") or "", r.get("robots", ""))
        print(r["body"][:1500].decode("utf-8", "replace"))
        return 0
    chosen = [s for s in SOURCES if not a.only or s["id"] in a.only]
    results = []
    for spec in chosen:
        print(f"probing {spec['id']} ...", file=sys.stderr, flush=True)
        results.append(run_source(F, spec))
    doc = {
        "run_date": a.date,
        "user_agent": UA,
        "pdf_text_library_available": pdf_text(b"%PDF-1.4", 1) is not None,
        "method": {
            "rate_limit": "at most 1 request/second per host; robots.txt Crawl-delay honored",
            "robots": "robots.txt fetched per host; 401/403 treated as no-crawl; disallowed paths skipped",
            "samples": "Socrata $limit=5; bulk files read with HTTP Range (200 bytes) or capped at 1.5-8 MB",
            "verdicts": "VERIFIED = data retrieved this run; PARTIAL = documents/portal only or partly retrieved; BLOCKED = auth/key/WAF/CDN denial; NOT FOUND = no usable endpoint found",
        },
        "ranking_ingest_next": RANKING,
        "sources": results,
        "summary": [
            {
                "id": s["id"],
                "name": s["name"],
                "cases": s["cases"],
                "verdict": s["verdict"],
                "access": s["access_method"],
                "cost": s["cost"],
                "signal_quality": s["signal_quality_for_brickline"],
            }
            for s in results
        ],
    }
    suffix = ".partial" if a.only and not a.merge else ""
    if a.only and a.merge:
        full = Path(a.out) / f"source-verification-{a.date}.json"
        old = json.loads(full.read_text())
        fresh = {r["id"]: r for r in results}
        merged = [fresh.get(x["id"], x) for x in old["sources"]]
        results = merged
        doc["sources"] = merged
        doc["summary"] = [
            {
                "id": x["id"],
                "name": x["name"],
                "cases": x["cases"],
                "verdict": x["verdict"],
                "access": x["access_method"],
                "cost": x["cost"],
                "signal_quality": x["signal_quality_for_brickline"],
            }
            for x in merged
        ]
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    stem = f"source-verification-{a.date}{suffix}"
    (out / f"{stem}.json").write_text(json.dumps(doc, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
    (out / f"{stem}.md").write_text(render_md(doc))
    print(f"wrote {out / (stem + '.json')} and .md ({len(results)} sources)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
