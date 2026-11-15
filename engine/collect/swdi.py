"""NOAA SWDI NEXRAD Level-3 hail signatures (nx3hail) for the Chicago area.

Each row is a radar-detected hail cell at one scan time: probability of hail (PROB), probability of severe
hail (SEVPROB), estimated maximum size in inches (MAXSIZE) and the cell centroid. The service caps a request
at 744 hours, so data is fetched one month at a time into data/raw/swdi/nx3hail-<yyyymm>.csv (resumable;
finished months are not re-fetched).
"""

from __future__ import annotations

import time
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

BASE = "https://www.ncei.noaa.gov/swdiws/csv/nx3hail"
BBOX = "-87.95,41.62,-87.50,42.05"  # minLon,minLat,maxLon,maxLat around the City of Chicago
HEADER = "ZTIME,WSR_ID,CELL_ID,PROB,SEVPROB,MAXSIZE,LAT,LON"


def _fetch(url: str, attempts: int = 5) -> str:
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(url, timeout=180) as resp:
                return resp.read().decode("utf-8", "replace")
        except (urllib.error.URLError, TimeoutError) as exc:
            if attempt == attempts - 1:
                raise RuntimeError(f"download failed after {attempts} attempts: {url}") from exc
            time.sleep(4 * 2**attempt)
    raise AssertionError("unreachable")


def sync(out_dir: Path, years: range = range(2016, 2027), log=print) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    today = date.today()
    for year in years:
        for month in range(1, 13):
            start = date(year, month, 1)
            if start > today:
                return
            path = out_dir / f"nx3hail-{year}{month:02d}.csv"
            current = (start.year, start.month) >= (today.year, today.month)
            if path.exists() and not current:
                continue
            end = date(year + (month == 12), month % 12 + 1, 1)
            url = f"{BASE}/{start:%Y%m%d}:{end:%Y%m%d}/1000000?bbox={BBOX}"
            body = _fetch(url)
            lines = [
                ln for ln in body.splitlines() if ln and not ln.startswith(("summary", "count", "totalTime"))
            ]
            if lines and lines[0].startswith("error"):
                raise RuntimeError(f"SWDI error for {start:%Y-%m}: {lines[0]}")
            rows = [ln for ln in lines if not ln.startswith("ZTIME")]
            tmp = path.with_suffix(".tmp")
            tmp.write_text("\n".join([HEADER, *rows]) + "\n")
            tmp.rename(path)
            if rows:
                log(f"  swdi {year}-{month:02d}: {len(rows)} hail-cell detections")
