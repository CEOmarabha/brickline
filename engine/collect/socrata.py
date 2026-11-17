"""Bulk export from Socrata (Tyler Data & Insights) open-data portals to local CSV pages."""

from __future__ import annotations

import csv
import urllib.parse
from pathlib import Path

from engine.collect.http import get_bytes

csv.field_size_limit(2**24)


def export_csv(
    domain: str,
    dataset: str,
    select: str,
    where: str | None,
    out_dir: Path,
    page_size: int = 200_000,
    log=print,
) -> list[Path]:
    """Download every row matching `where` as CSV pages ordered by the internal row id.

    Pages are written atomically, so an interrupted run can resume where it stopped.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    pages: list[Path] = []
    offset = 0
    while True:
        path = out_dir / f"page-{offset // page_size:04d}.csv"
        if not path.exists():
            params = {"$select": select, "$order": ":id", "$limit": str(page_size), "$offset": str(offset)}
            if where:
                params["$where"] = where
            url = f"https://{domain}/resource/{dataset}.csv?{urllib.parse.urlencode(params)}"
            body = get_bytes(url)
            tmp = path.with_suffix(".tmp")
            tmp.write_bytes(body)
            tmp.rename(path)
            log(f"  {dataset}: page {offset // page_size} ({len(body) / 1e6:.1f} MB)")
        pages.append(path)
        if count_rows(path) < page_size:
            return pages
        offset += page_size


def count_rows(path: Path) -> int:
    """Data rows of a CSV page. Counted as records, not lines: quoted fields can hold line breaks."""
    with path.open(newline="", encoding="utf-8", errors="replace") as fh:
        return max(0, sum(1 for _ in csv.reader(fh)) - 1)
