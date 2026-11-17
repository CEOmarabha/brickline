"""Overture Maps Places (open data, CDLA-Permissive-2.0) for the Chicago metro, as a small GeoParquet subset.

Overture publishes the whole world as GeoParquet on S3 (anonymous access). One DuckDB query with httpfs reads
only the row groups whose bbox struct overlaps the area we ask for, so the subset downloads in seconds.
Writes data/raw/overture/places-<release>.parquet (resumable: an existing file for the latest release is kept).

Attribution (required by Overture): "Places data (c) Overture Maps Foundation, CDLA-Permissive-2.0;
sources include Meta and Microsoft"; see docs/data-source-registry.md.
"""

from __future__ import annotations

import re
from pathlib import Path

import duckdb

from engine.collect.http import FetchError, get_bytes

BUCKET = "overturemaps-us-west-2"
REGION = "us-west-2"
# Chicago city bounding box (the area the app is about) and a metro box around it. Many Chicago contractors
# are based in the suburbs, so the subset covers the metro. The warehouse column `in_chicago` marks places
# inside the city box whose locality is Chicago (or, with no locality, a 606xx ZIP): the box alone also
# contains western suburbs such as Oak Brook.
CHICAGO_BBOX = (41.64, 42.03, -87.95, -87.52)  # lat min, lat max, lon min, lon max
METRO_BBOX = (41.45, 42.30, -88.45, -87.45)

COLUMNS = (
    "id, name, category, categories, phones, websites, emails, address, locality, postcode, region, "
    "confidence, status, lat, lon, release"
)


def latest_release() -> str:
    """Newest release folder name (e.g. '2026-10-21.0') from the public bucket listing."""
    url = f"https://{BUCKET}.s3.amazonaws.com/?list-type=2&prefix=release/&delimiter=/"
    body = get_bytes(url, timeout=60, attempts=3).decode()
    releases = re.findall(r"<Prefix>release/(\d{4}-\d{2}-\d{2}\.\d+)/</Prefix>", body)
    if not releases:
        raise FetchError(f"no Overture releases listed at {url}")
    return max(releases, key=lambda r: tuple(int(x) for x in re.split(r"[-.]", r)))


def _category_exprs(con: duckdb.DuckDBPyConnection, src: str) -> tuple[str, str]:
    """Primary and alternate category expressions: releases carry either `taxonomy` or the older `categories`."""
    cols = {
        r[0]
        for r in con.execute(f"DESCRIBE SELECT * FROM read_parquet('{src}', hive_partitioning=1)").fetchall()
    }
    if "taxonomy" in cols:
        return "taxonomy.primary", "taxonomy.alternates"
    return "categories.primary", "categories.alternate"


def sync(out_dir: Path, log=print) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    release = latest_release()
    out = out_dir / f"places-{release}.parquet"
    if out.exists():
        log(f"  overture {release}: already downloaded ({out.stat().st_size / 1e6:.0f} MB)")
        return out
    src = f"s3://{BUCKET}/release/{release}/theme=places/type=place/*"
    con = duckdb.connect()
    con.execute("INSTALL httpfs; LOAD httpfs; INSTALL spatial; LOAD spatial;")
    con.execute(f"SET s3_region='{REGION}'")
    primary, alternates = _category_exprs(con, src)
    lat0, lat1, lon0, lon1 = METRO_BBOX
    tmp = out.with_suffix(".tmp")
    con.execute(f"""
        COPY (
            SELECT id, names.primary AS name, {primary} AS category, {alternates} AS categories,
                phones, websites, emails,
                addresses[1].freeform AS address, addresses[1].locality AS locality,
                addresses[1].postcode AS postcode, addresses[1].region AS region,
                confidence, operating_status AS status,
                ST_Y(geometry) AS lat, ST_X(geometry) AS lon, '{release}' AS release
            FROM read_parquet('{src}', hive_partitioning=1)
            WHERE bbox.xmin BETWEEN {lon0} AND {lon1} AND bbox.ymin BETWEEN {lat0} AND {lat1}
              AND names.primary IS NOT NULL
            ORDER BY id
        ) TO '{tmp}' (FORMAT parquet, COMPRESSION zstd)
    """)
    con.close()
    tmp.rename(out)
    for old in out_dir.glob("places-*.parquet"):
        if old != out:
            old.unlink()
    n = duckdb.connect().execute(f"SELECT count(*) FROM read_parquet('{out}')").fetchone()[0]
    log(f"  overture {release}: {n:,} places ({out.stat().st_size / 1e6:.0f} MB)")
    return out
