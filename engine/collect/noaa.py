"""NOAA Storm Events (NCEI) for Cook County, IL: hail, damaging wind and similar events with coordinates.

Writes data/raw/noaa/storms-<year>.csv (one file per year, resumable).
"""

from __future__ import annotations

import csv
import gzip
import io
import re
import urllib.request
from pathlib import Path

BASE = "https://www.ncei.noaa.gov/pub/data/swdi/stormevents/csvfiles/"
KEEP = (
    "Hail",
    "Thunderstorm Wind",
    "High Wind",
    "Tornado",
    "Heavy Rain",
    "Flood",
    "Flash Flood",
    "Winter Storm",
)
FIELDS = [
    "event_id",
    "begin_date_time",
    "event_type",
    "magnitude",
    "lat",
    "lon",
    "location",
    "damage_property",
]


def sync(out_dir: Path, years: range = range(2010, 2027), log=print) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(BASE, timeout=120) as resp:
        index = resp.read().decode()
    for year in years:
        path = out_dir / f"storms-{year}.csv"
        if path.exists() and year < max(years):
            continue
        names = sorted(set(re.findall(rf"StormEvents_details-ftp_v1\.0_d{year}_c\d+\.csv\.gz", index)))
        if not names:
            continue
        with urllib.request.urlopen(BASE + names[-1], timeout=600) as resp:
            raw = gzip.decompress(resp.read()).decode("latin-1")
        rows = []
        for r in csv.DictReader(io.StringIO(raw)):
            if r["STATE"] != "ILLINOIS" or r["CZ_NAME"] != "COOK" or r["EVENT_TYPE"] not in KEEP:
                continue
            rows.append(
                {
                    "event_id": r["EVENT_ID"],
                    "begin_date_time": r["BEGIN_DATE_TIME"],
                    "event_type": r["EVENT_TYPE"],
                    "magnitude": r["MAGNITUDE"],
                    "lat": r["BEGIN_LAT"],
                    "lon": r["BEGIN_LON"],
                    "location": r["BEGIN_LOCATION"],
                    "damage_property": r["DAMAGE_PROPERTY"],
                }
            )
        tmp = path.with_suffix(".tmp")
        with tmp.open("w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=FIELDS)
            w.writeheader()
            w.writerows(rows)
        tmp.rename(path)
        log(f"  noaa {year}: {len(rows)} Cook County events")
