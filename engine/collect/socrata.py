"""Bulk export from Socrata (Tyler Data & Insights) open-data portals to local CSV pages."""

from __future__ import annotations

import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


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
            body = _get(url)
            tmp = path.with_suffix(".tmp")
            tmp.write_bytes(body)
            tmp.rename(path)
            log(f"  {dataset}: page {offset // page_size} ({len(body) / 1e6:.1f} MB)")
        pages.append(path)
        with path.open("rb") as fh:
            rows = sum(1 for _ in fh) - 1
        if rows < page_size:
            return pages
        offset += page_size


def _get(url: str, attempts: int = 5) -> bytes:
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(url, timeout=600) as resp:
                return resp.read()
        except (urllib.error.URLError, TimeoutError) as exc:
            if attempt == attempts - 1:
                raise RuntimeError(f"download failed after {attempts} attempts: {url}") from exc
            time.sleep(4 * 2**attempt)
    raise AssertionError("unreachable")
