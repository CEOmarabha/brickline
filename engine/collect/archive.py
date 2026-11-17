"""Weekly archive of public sources that publish only their CURRENT state (no history).

Each run writes one gzip CSV per source: data/archive/<name>/<YYYY-MM-DD>.csv.gz (rows sorted by primary key,
deterministic bytes), mirrors it to the persistent agent store when one is mounted, and records rows and the
sha256 of the CSV content in research/archive/manifest.json (committed). Existing dates are never overwritten
unless --force. A source that fails is recorded in the manifest and the run continues.

    uv run python -m engine.collect.archive                      # every source
    uv run python -m engine.collect.archive --only fmcsa_chicago_carriers idph_hospitals
    uv run python -m engine.collect.archive --diff idph_hospitals 2026-11-16 2026-11-23

Polite: descriptive User-Agent, at most one request per second per host, retries with backoff. The Socrata
endpoints are the portals' documented public APIs (no key); HFSRB pages are fetched through
engine.collect.hfsrb.Fetcher, which checks robots.txt before every request. Nothing bypasses authentication,
robots.txt or CAPTCHAs.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import http.client
import io
import json
import os
import shutil
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path

from engine.collect import hfsrb

UA = hfsrb.UA
ARCHIVE_DIR = Path("data/archive")
MANIFEST = Path("research/archive/manifest.json")
STORE_ROOT = Path(os.environ.get("BRICKLINE_ARCHIVE_STORE", "/cursor/stores/self/brickline-archive"))
PAGE_SIZE = 50_000


class Http:
    """GET with a descriptive User-Agent, a minimum interval per host and retries with backoff."""

    def __init__(self, min_interval: float = 1.0, attempts: int = 5) -> None:
        self.min_interval = min_interval
        self.attempts = attempts
        self.last: dict[str, float] = {}

    def get(self, url: str) -> bytes:
        host = urllib.parse.urlsplit(url).netloc
        for attempt in range(self.attempts):
            wait = self.min_interval - (time.monotonic() - self.last.get(host, -1e9))
            if wait > 0:
                time.sleep(wait)
            self.last[host] = time.monotonic()
            try:
                req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/csv"})
                with urllib.request.urlopen(req, timeout=300) as resp:
                    return resp.read()
            except urllib.error.HTTPError as exc:
                retryable = exc.code == 429 or exc.code >= 500
                if not retryable or attempt == self.attempts - 1:
                    raise RuntimeError(f"HTTP {exc.code} for {url}") from exc
            except (OSError, http.client.HTTPException) as exc:
                if attempt == self.attempts - 1:
                    raise RuntimeError(
                        f"download failed after {self.attempts} attempts: {url} ({exc})"
                    ) from exc
            time.sleep(4 * 2**attempt)
        raise AssertionError("unreachable")


HTTP = Http()


@dataclass
class Context:
    run_date: date
    log: Callable[[str], None] = lambda m: print(m, flush=True)
    cache: dict | None = None


@dataclass(frozen=True)
class Spec:
    name: str
    description: str
    url: str
    fields: tuple[str, ...]
    key: tuple[str, ...]
    fetch: Callable[[Context], list[dict]]
    filter: str = ""


def socrata_fetch(domain: str, dataset: str, fields: tuple[str, ...], where: str = "") -> Callable:
    def fetch(ctx: Context) -> list[dict]:
        rows: list[dict] = []
        offset = 0
        while True:
            params = {
                "$select": ", ".join(fields),
                "$order": ":id",
                "$limit": str(PAGE_SIZE),
                "$offset": str(offset),
            }
            if where:
                params["$where"] = where
            url = f"https://{domain}/resource/{dataset}.csv?{urllib.parse.urlencode(params)}"
            body = HTTP.get(url).decode("utf-8-sig")
            page = list(csv.DictReader(io.StringIO(body)))
            missing = [f for f in fields if page and f not in page[0]]
            if missing:
                raise RuntimeError(f"fields missing from response: {missing}")
            rows.extend({f: r.get(f) or "" for f in fields} for r in page)
            ctx.log(f"    {dataset}: {len(rows)} rows")
            if len(page) < PAGE_SIZE:
                return rows
            offset += PAGE_SIZE

    return fetch


def socrata_spec(
    name: str,
    description: str,
    domain: str,
    dataset: str,
    fields: tuple[str, ...],
    key: tuple[str, ...],
    where: str = "",
) -> Spec:
    return Spec(
        name=name,
        description=description,
        url=f"https://{domain}/resource/{dataset}.csv",
        fields=fields,
        key=key,
        fetch=socrata_fetch(domain, dataset, fields, where),
        filter=where,
    )


def _hfsrb_items(ctx: Context) -> tuple[hfsrb.Fetcher, list[dict]]:
    """One shared Fetcher and listing request per run (the list and page specs both need them)."""
    if ctx.cache is None:
        ctx.cache = {}
    if "hfsrb" not in ctx.cache:
        fetcher = hfsrb.Fetcher()
        _, items = hfsrb.fetch_listing(fetcher)
        ctx.cache["hfsrb"] = (fetcher, items)
    return ctx.cache["hfsrb"]


HFSRB_LIST_FIELDS = (
    "page_url",
    "project_no",
    "project_name",
    "facility_name",
    "city_in_name",
    "project_year",
    "project_status",
    "deemed_complete",
)


def _hfsrb_page_url(link: str) -> str:
    return hfsrb.BASE + link.replace("/content/soi/hfsrb/en/", "/") if link else ""


def fetch_hfsrb_list(ctx: Context) -> list[dict]:
    _, items = _hfsrb_items(ctx)
    rows = []
    for it in items:
        link = it.get("meta", {}).get("dynamicPageLink", "")
        num, facility, city, name = hfsrb.split_name(it["projectName"], link)
        rows.append(
            {
                "page_url": _hfsrb_page_url(link),
                "project_no": num,
                "project_name": name,
                "facility_name": facility,
                "city_in_name": city,
                "project_year": it.get("projectYear") or "",
                "project_status": it.get("projectStatus") or "",
                "deemed_complete": (it.get("projectDeemedComplete") or "").lower(),
            }
        )
    ctx.log(f"    hfsrb listing: {len(rows)} projects")
    return rows


HFSRB_PAGE_FIELDS = (
    "page_url",
    "project_no",
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
    "page_status",
)


def fetch_hfsrb_pages(ctx: Context) -> list[dict]:
    """Fresh copy of every project page for projects of last year and this year (about 185 requests)."""
    fetcher, items = _hfsrb_items(ctx)
    first_year = ctx.run_date.year - 1
    todo: dict[str, str] = {}
    for it in items:
        link = it.get("meta", {}).get("dynamicPageLink", "")
        year = it.get("projectYear") or ""
        if link and year.isdigit() and int(year) >= first_year:
            num, *_ = hfsrb.split_name(it["projectName"], link)
            todo.setdefault(_hfsrb_page_url(link), num)
    rows: list[dict] = []
    consecutive_errors = 0
    for url, num in sorted(todo.items()):
        row = {f: "" for f in HFSRB_PAGE_FIELDS}
        row.update(page_url=url, project_no=num, document_count="0")
        try:
            html_text = fetcher.get(url).decode("utf-8", "replace")
            consecutive_errors = 0
        except urllib.error.HTTPError as exc:
            row["page_status"] = f"http {exc.code}"
        except (RuntimeError, PermissionError) as exc:
            consecutive_errors += 1
            row["page_status"] = "error"
            if consecutive_errors >= 5:
                raise RuntimeError(f"5 consecutive page failures, last: {exc}") from exc
        else:
            parsed = hfsrb.parse_page(html_text)
            for col in hfsrb.DATE_FIELDS.values():
                row[col] = parsed[col]
            row["document_count"] = str(len(parsed["documents"]))
            for col, pat in hfsrb.DOC_KINDS:
                row[col] = hfsrb.pick_doc(parsed["documents"], pat)
            row["page_status"] = "ok"
        rows.append(row)
    ctx.log(f"    hfsrb pages: {len(rows)} fetched")
    return rows


FMCSA_FIELDS = (
    "dot_number",
    "legal_name",
    "dba_name",
    "phy_street",
    "phy_city",
    "phy_state",
    "phy_zip",
    "phy_cnty",
    "status_code",
    "carrier_operation",
    "classdef",
    "business_org_desc",
    "add_date",
    "mcs150_date",
    "mcs150_mileage",
    "mcs150_mileage_year",
    "mcs150_update_code_id",
    "power_units",
    "truck_units",
    "bus_units",
    "fleetsize",
    "total_drivers",
    "total_cdl",
    "total_intrastate_drivers",
    "driver_inter_total",
    "hm_ind",
    "safety_rating",
    "safety_rating_date",
    "prior_revoke_flag",
)

ADU_FIELDS = (
    "id",
    "submission_date",
    "status",
    "address",
    "zip",
    "ward",
    "zoning",
    "latitude",
    "longitude",
    "coach_house",
    "conversion_unit",
    "adu_applying_for",
    "dwelling_units_in_lot",
    "max_number_of_adu_allowed",
    "max_number_coach_house_units_allowed",
    "principal_building_built_year",
    "number_affordable_units_required",
    "property_owner_occupied",
    "user_amended_date",
    "action_date",
)

BUYING_PLAN_FIELDS = (
    "buying_plan_number",
    "contract_commodity_category",
    "department",
    "current_contract_number",
    "project_description",
    "estimated_total_contract",
    "estimated_contract_term",
    "anticipated_advertise_date",
    "proposed_procurement_method",
)

HOSPITAL_FIELDS = (
    "license_number",
    "facility_name",
    "facility_type",
    "address",
    "city",
    "county",
    "zip",
    "phone",
    "exp_date",
)

ASTC_FIELDS = (
    "license_number",
    "facility_name",
    "address",
    "city",
    "county",
    "zip",
    "contact_name",
    "phone",
    "exp_date",
)

SPECS: tuple[Spec, ...] = (
    socrata_spec(
        "fmcsa_chicago_carriers",
        "FMCSA Company Census File: carriers with a Chicago, IL physical address. Current state only; the "
        "open file has no history, so weekly power-unit, driver and MCS-150 changes need our own snapshots "
        "(E23). Contact fields (phone, email, officers) are deliberately not kept.",
        "data.transportation.gov",
        "az4n-8mr2",
        FMCSA_FIELDS,
        ("dot_number",),
        "phy_city='CHICAGO' AND phy_state='IL'",
    ),
    Spec(
        "hfsrb_projects",
        "Illinois HFSRB project search listing (CON and exemption projects): project number, facility, "
        "type (Exempted / Non-Exempted) and deemed-complete flag. List only, no PDFs. New projects and "
        "status flips become visible week to week (E20).",
        hfsrb.LISTING,
        HFSRB_LIST_FIELDS,
        ("page_url", "project_name", "project_year"),
        fetch_hfsrb_list,
    ),
    Spec(
        "hfsrb_project_pages",
        "Illinois HFSRB per-project pages for projects of last year and this year: received date, "
        "hearing and comment deadlines, Board meeting date and which documents exist (application, "
        "completeness letter, staff report, approval letter). Board-action progress shows as these "
        "dates and links appearing (E20).",
        hfsrb.BASE + "/project/project-search.html",
        HFSRB_PAGE_FIELDS,
        ("page_url",),
        fetch_hfsrb_pages,
    ),
    socrata_spec(
        "cook_buying_plan",
        "Cook County Procurement Buying Plan (fiscal year 2026, dataset cbhc-xvrm): planned solicitations "
        "with category, department, value band and anticipated advertise quarter. Items appearing, "
        "changing quarter or disappearing (posted) are the forward-looking events (E24). A new fiscal "
        "year gets a new dataset id: add it here when the County publishes it.",
        "datacatalog.cookcountyil.gov",
        "cbhc-xvrm",
        BUYING_PLAN_FIELDS,
        ("buying_plan_number", "project_description"),
    ),
    socrata_spec(
        "chicago_adu_preapprovals",
        "Chicago Additional Dwelling Unit preapproval applications (Socrata j4h8-ug9m), with status and "
        "action dates. Applicant and owner names are not kept. Status moves (Submitted -> Pre-Certified) "
        "and a later building permit at the address are the test chain for ADU preapproval -> permit.",
        "data.cityofchicago.org",
        "j4h8-ug9m",
        ADU_FIELDS,
        ("id",),
    ),
    socrata_spec(
        "idph_hospitals",
        "Illinois IDPH Hospital Directory (all Illinois hospitals; Socrata 53nt-jwqq on the Illinois open "
        "data portal): licence number, facility, type, address, licence expiry. New or closed hospitals "
        "and address changes (E20 facility master list).",
        "illinois-edp.data.socrata.com",
        "53nt-jwqq",
        HOSPITAL_FIELDS,
        ("license_number",),
    ),
    socrata_spec(
        "idph_astc",
        "Illinois IDPH Ambulatory Surgical Treatment Center Directory (all Illinois ASTCs; Socrata "
        "79iq-26tb): licence number, facility, address, administrative contact, licence expiry. New or "
        "closed surgery centers (E20 facility master list).",
        "illinois-edp.data.socrata.com",
        "79iq-26tb",
        ASTC_FIELDS,
        ("license_number",),
    ),
)
SPEC_BY_NAME = {s.name: s for s in SPECS}


def _sort_part(value: str) -> tuple:
    return (0, int(value), "") if value.isdigit() else (1, 0, value)


def row_key(spec: Spec, row: dict) -> tuple:
    return tuple(_sort_part(row[k]) for k in spec.key)


def encode_csv(spec: Spec, rows: list[dict]) -> bytes:
    ordered = sorted(rows, key=lambda r: (row_key(spec, r), [r[f] for f in spec.fields]))
    buf = io.StringIO(newline="")
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(spec.fields)
    for r in ordered:
        w.writerow([r[f] for f in spec.fields])
    return buf.getvalue().encode("utf-8")


def gzip_bytes(data: bytes) -> bytes:
    return gzip.compress(data, compresslevel=9, mtime=0)


def local_path(name: str, day: str) -> Path:
    return ARCHIVE_DIR / name / f"{day}.csv.gz"


def store_dir(name: str) -> Path | None:
    if STORE_ROOT.parent.is_dir() and os.access(STORE_ROOT.parent, os.W_OK):
        return STORE_ROOT / name
    return None


def mirror_to_store(name: str, src: Path, force: bool) -> bool:
    dest_dir = store_dir(name)
    if dest_dir is None:
        return False
    try:
        dest = dest_dir / src.name
        if dest.exists() and not force:
            return False
        dest_dir.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_suffix(".tmp")
        shutil.copyfile(src, tmp)
        tmp.replace(dest)
        return True
    except OSError:
        return False


def restore_from_store(name: str) -> int:
    """Copy snapshots the store holds but this checkout lacks (a fresh VM)."""
    src_dir = store_dir(name)
    if src_dir is None or not src_dir.is_dir():
        return 0
    restored = 0
    for f in sorted(src_dir.glob("*.csv.gz")):
        dest = ARCHIVE_DIR / name / f.name
        if not dest.exists():
            try:
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(f, dest)
                restored += 1
            except OSError:
                pass
    return restored


def read_snapshot(path: Path) -> tuple[bytes, list[dict]]:
    data = gzip.decompress(path.read_bytes())
    return data, list(csv.DictReader(io.StringIO(data.decode("utf-8"), newline="")))


def load_manifest() -> dict:
    if MANIFEST.exists():
        return json.loads(MANIFEST.read_text())
    return {"sources": []}


def save_manifest(manifest: dict) -> bool:
    manifest["sources"].sort(key=lambda s: s["name"])
    for s in manifest["sources"]:
        s["runs"].sort(key=lambda r: r["date"])
    text = json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"
    if MANIFEST.exists() and MANIFEST.read_text() == text:
        return False
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    tmp = MANIFEST.with_suffix(".tmp")
    tmp.write_text(text)
    tmp.replace(MANIFEST)
    return True


def manifest_source(manifest: dict, spec: Spec) -> dict:
    entry = next((s for s in manifest["sources"] if s["name"] == spec.name), None)
    if entry is None:
        entry = {"runs": []}
        manifest["sources"].append(entry)
    runs = entry["runs"]
    entry.clear()
    entry.update(
        name=spec.name,
        description=spec.description,
        url=spec.url,
        filter=spec.filter,
        fields=list(spec.fields),
        key=list(spec.key),
        runs=runs,
    )
    return entry


def record_run(entry: dict, run: dict) -> None:
    """Replace the entry for this date, except that a failure never overwrites a successful run."""
    existing = next((r for r in entry["runs"] if r["date"] == run["date"]), None)
    if existing is not None:
        if existing["status"] == "ok" and run["status"] != "ok":
            return
        entry["runs"].remove(existing)
    entry["runs"].append(run)


def run_entry_for_file(day: str, path: Path) -> dict:
    data, rows = read_snapshot(path)
    return {"date": day, "rows": len(rows), "sha256": hashlib.sha256(data).hexdigest(), "status": "ok"}


def duplicate_keys(spec: Spec, rows: list[dict]) -> int:
    seen: set[tuple] = set()
    dups = 0
    for r in rows:
        k = tuple(r[f] for f in spec.key)
        dups += k in seen
        seen.add(k)
    return dups


def archive(
    only: list[str] | None = None,
    force: bool = False,
    run_date: date | None = None,
    log: Callable[[str], None] = lambda m: print(m, flush=True),
) -> list[dict]:
    day = (run_date or datetime.now(UTC).date()).isoformat()
    ctx = Context(run_date=date.fromisoformat(day), log=log)
    manifest = load_manifest()
    results = []
    for spec in SPECS:
        if only and spec.name not in only:
            continue
        entry = manifest_source(manifest, spec)
        restore_from_store(spec.name)
        path = local_path(spec.name, day)
        result = {"name": spec.name, "date": day, "status": "ok", "bytes": 0, "rows": 0, "action": ""}
        if path.exists() and not force:
            if not any(r["date"] == day and r["status"] == "ok" for r in entry["runs"]):
                record_run(entry, run_entry_for_file(day, path))
            run = next(r for r in entry["runs"] if r["date"] == day)
            result.update(rows=run["rows"], bytes=path.stat().st_size, action="exists, not overwritten")
            mirror_to_store(spec.name, path, force=False)
            log(f"{spec.name}: {day} already archived ({run['rows']} rows), skipped")
            results.append(result)
            continue
        log(f"{spec.name}: fetching")
        try:
            rows = spec.fetch(ctx)
            if not rows:
                raise RuntimeError("empty response (0 rows); nothing archived")
            data = encode_csv(spec, rows)
            blob = gzip_bytes(data)
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(".tmp")
            tmp.write_bytes(blob)
            tmp.replace(path)
            run = {"date": day, "rows": len(rows), "sha256": hashlib.sha256(data).hexdigest(), "status": "ok"}
            dups = duplicate_keys(spec, rows)
            if dups:
                run["duplicate_keys"] = dups
            record_run(entry, run)
            mirrored = mirror_to_store(spec.name, path, force=force)
            result.update(
                rows=len(rows), bytes=len(blob), action="written" + (" + store" if mirrored else "")
            )
            log(f"{spec.name}: {len(rows)} rows, {len(blob) / 1e3:.0f} KB gz -> {path}")
        except Exception as exc:
            msg = " ".join(f"{type(exc).__name__}: {exc}".split())[:300]
            record_run(entry, {"date": day, "rows": 0, "sha256": None, "status": f"error: {msg}"})
            result.update(status=f"error: {msg}", action="failed")
            log(f"{spec.name}: FAILED {msg}")
        results.append(result)
    if save_manifest(manifest):
        log(f"manifest updated: {MANIFEST}")
    else:
        log("manifest unchanged")
    return results


def _load_for_diff(name: str, day: str) -> list[dict]:
    path = local_path(name, day)
    if not path.exists():
        restore_from_store(name)
    if not path.exists():
        raise FileNotFoundError(f"no snapshot for {name} on {day} ({path})")
    return read_snapshot(path)[1]


def diff_snapshots(name: str, date_a: str, date_b: str) -> dict:
    """Compare two snapshots of one source.

    Returns {'added': [keys in B only], 'removed': [keys in A only], 'changed': {key: {field: (a, b)}},
    'changed_fields': {field: number of keys where it changed}}. Keys are the primary-key values joined with
    '|'; duplicate keys keep the last row.
    """
    spec = SPEC_BY_NAME[name]

    def index(rows: list[dict]) -> dict[str, dict]:
        return {"|".join(r[k] for k in spec.key): r for r in rows}

    a, b = index(_load_for_diff(name, date_a)), index(_load_for_diff(name, date_b))
    changed: dict[str, dict[str, tuple[str, str]]] = {}
    fields: dict[str, int] = {}
    for k in sorted(a.keys() & b.keys()):
        delta = {f: (a[k][f], b[k][f]) for f in spec.fields if a[k][f] != b[k][f]}
        if delta:
            changed[k] = delta
            for f in delta:
                fields[f] = fields.get(f, 0) + 1
    return {
        "added": sorted(b.keys() - a.keys()),
        "removed": sorted(a.keys() - b.keys()),
        "changed": changed,
        "changed_fields": dict(sorted(fields.items())),
    }


def print_diff(name: str, date_a: str, date_b: str, limit: int = 10) -> dict:
    d = diff_snapshots(name, date_a, date_b)
    print(f"{name}: {date_a} -> {date_b}")
    print(f"  added {len(d['added'])}, removed {len(d['removed'])}, changed {len(d['changed'])}")
    print(f"  changed fields: {d['changed_fields'] or 'none'}")
    for label in ("added", "removed"):
        for k in d[label][:limit]:
            print(f"  {label}: {k}")
    for k in list(d["changed"])[:limit]:
        print(f"  changed: {k}: {d['changed'][k]}")
    return d


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument(
        "--only", nargs="+", metavar="NAME", help=f"sources to archive: {', '.join(SPEC_BY_NAME)}"
    )
    ap.add_argument("--force", action="store_true", help="overwrite an existing file for the run date")
    ap.add_argument("--date", help="run date YYYY-MM-DD (default: today, UTC)")
    ap.add_argument("--diff", nargs=3, metavar=("NAME", "DATE_A", "DATE_B"), help="compare two snapshots")
    a = ap.parse_args()
    if a.diff:
        if a.diff[0] not in SPEC_BY_NAME:
            ap.error(f"unknown source {a.diff[0]}")
        print_diff(*a.diff)
        return 0
    unknown = [n for n in (a.only or []) if n not in SPEC_BY_NAME]
    if unknown:
        ap.error(f"unknown source(s): {', '.join(unknown)}")
    results = archive(a.only, a.force, date.fromisoformat(a.date) if a.date else None)
    failed = [r for r in results if r["status"] != "ok"]
    print(f"\n{len(results) - len(failed)} of {len(results)} sources archived or already present")
    for r in failed:
        print(f"  FAILED {r['name']}: {r['status']}", file=sys.stderr)
    return 2 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
