"""CFPB HMDA home-improvement loans (loan_purpose=2, originated) for Cook County, IL, by census tract.

Uses the FFIEC HMDA Data Browser API (annual files, no key). The browser redirects to a prebuilt CSV on
files.ffiec.cfpb.gov. Writes data/raw/hmda/hmda-<year>.csv (one file per year, resumable).
Tract vintage: 2018-2021 loans use 2010 census tracts, 2022 onward use 2020 tracts.
"""

from __future__ import annotations

import time
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

API = "https://ffiec.cfpb.gov/v2/data-browser-api/view/csv"


def _fetch(url: str, attempts: int = 5) -> bytes:
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(url, timeout=600) as resp:  # follows the redirect to the file host
                return resp.read()
        except (urllib.error.URLError, TimeoutError) as exc:
            if attempt == attempts - 1:
                raise RuntimeError(f"download failed after {attempts} attempts: {url}") from exc
            time.sleep(4 * 2**attempt)
    raise AssertionError("unreachable")


def sync(out_dir: Path, years: range = range(2018, date.today().year), log=print) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for year in years:
        path = out_dir / f"hmda-{year}.csv"
        if path.exists():
            continue
        url = f"{API}?counties=17031&years={year}&loan_purposes=2&actions_taken=1"
        body = _fetch(url)
        if not body.startswith(b"activity_year"):
            log(f"  hmda {year}: not available")
            continue
        tmp = path.with_suffix(".tmp")
        tmp.write_bytes(body)
        tmp.rename(path)
        loans = body.count(b"\n") - 1
        log(f"  hmda {year}: {loans} Cook County home-improvement loans")
