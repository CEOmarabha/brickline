"""Local analytical warehouse of Chicago / Cook County public records.

    uv run python -m engine.warehouse sync     # download raw CSV pages (resumable)
    uv run python -m engine.warehouse build    # (re)build normalized tables in data/warehouse.duckdb

Raw pages are kept under data/raw/<dataset>/ so tables can be rebuilt without re-downloading.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

import duckdb

from engine.classify.trades import PERMIT_TRADES, VIOLATION_TRADES, sql_flags
from engine.collect.socrata import export_csv

DATA = Path("data")
RAW = DATA / "raw"
DB_PATH = DATA / "warehouse.duckdb"

CHICAGO = "data.cityofchicago.org"
COOK = "datacatalog.cookcountyil.gov"
CHICAGO_TOWNSHIPS = ("70", "71", "72", "73", "74", "75", "76", "77")


@dataclass(frozen=True)
class Dataset:
    name: str
    domain: str
    dataset_id: str
    select: str
    where: str | None = None


CONTACT_COLS = ",".join(f"contact_{i}_type,contact_{i}_name" for i in range(1, 16))

DATASETS = [
    Dataset(
        "permits",
        CHICAGO,
        "ydr8-5enu",
        "id,permit_,permit_status,permit_milestone,permit_type,review_type,application_start_date,issue_date,"
        "processing_time,street_number,street_direction,street_name,work_type,work_description,"
        f"reported_cost,pin_list,community_area,latitude,longitude,{CONTACT_COLS}",
    ),
    Dataset(
        "violations",
        CHICAGO,
        "22u3-xenr",
        "id,violation_date,violation_code,violation_status,violation_status_date,violation_description,"
        "inspection_status,inspection_category,department_bureau,address,property_group,latitude,longitude",
        "violation_date >= '2010-01-01T00:00:00'",
    ),
    Dataset(
        "sales",
        COOK,
        "wvhk-k5uv",
        "pin,year,township_code,class,sale_date,sale_price,doc_no,deed_type,seller_name,buyer_name,"
        "is_multisale,num_parcels_sale,sale_filter_same_sale_within_365,sale_filter_less_than_10k,"
        "sale_filter_deed_type",
        "year >= 2010 AND township_code in(" + ",".join(f"'{t}'" for t in CHICAGO_TOWNSHIPS) + ")",
    ),
    Dataset(
        "food_licenses",
        CHICAGO,
        "r5kz-chrr",
        "license_id,account_number,legal_name,doing_business_as_name,address,license_description,"
        "application_type,application_created_date,date_issued,license_start_date,latitude,longitude",
        "license_description = 'Retail Food Establishment' AND application_type = 'ISSUE'",
    ),
]

# Address key: "<number> <dir> <street words up to and including the suffix>", unit/floor text dropped.
SUFFIXES = "AVE|AV|ST|BLVD|DR|RD|PL|CT|PKWY|TER|WAY|HWY|LN|SQ|PLZ|CIR|ROW|EXPY|PARK|CRES|PLAZA|SR|BL|TRL|WALK"
ADDRESS_RE = rf"^(\d+)\s+([NSEW])\s+(.*?\s(?:{SUFFIXES}))\b"
# Streets without a suffix (e.g. BROADWAY): number, direction, first street word.
ADDRESS_FALLBACK_RE = r"^(\d+ [NSEW] [A-Z0-9]+)"


def address_key_sql(expr: str) -> str:
    clean = f"regexp_replace(upper(trim({expr})), '\\s+', ' ', 'g')"
    return (
        f"coalesce(nullif(regexp_extract({clean}, '{ADDRESS_RE}', 1) || ' ' || "
        f"regexp_extract({clean}, '{ADDRESS_RE}', 2) || ' ' || "
        f"regexp_extract({clean}, '{ADDRESS_RE}', 3), '  '), "
        f"nullif(regexp_extract({clean}, '{ADDRESS_FALLBACK_RE}', 1), ''), {clean})"
    )


def sync(names: list[str] | None = None) -> None:
    for ds in DATASETS:
        if names and ds.name not in names:
            continue
        print(f"sync {ds.name} ({ds.domain}/{ds.dataset_id})")
        export_csv(ds.domain, ds.dataset_id, ds.select, ds.where, RAW / ds.name)


def _csv(name: str) -> str:
    return f"read_csv('{RAW / name}/page-*.csv', header=true, all_varchar=true, union_by_name=true)"


def build() -> None:
    DATA.mkdir(exist_ok=True)
    tmp = DB_PATH.with_suffix(".building")
    if tmp.exists():
        tmp.unlink()
    con = duckdb.connect(str(tmp))
    con.execute("SET preserve_insertion_order = false")

    print("build permits")
    con.execute(f"""
        CREATE TABLE permits AS
        WITH src AS (SELECT * FROM {_csv("permits")})
        SELECT
            id,
            permit_ AS permit_no,
            permit_status,
            permit_milestone,
            replace(permit_type, '–', '-') AS permit_type,
            work_type,
            try_cast(application_start_date AS TIMESTAMP)::DATE AS application_date,
            try_cast(issue_date AS TIMESTAMP)::DATE AS issue_date,
            try_cast(processing_time AS INTEGER) AS processing_days,
            try_cast(reported_cost AS DOUBLE) AS reported_cost,
            nullif(list_filter(
                list_transform(string_split(coalesce(pin_list, ''), '|'), lambda x: trim(x)),
                lambda x: length(x) >= 10 AND x NOT LIKE '0000000000%'
            )[1], '') AS pin10,
            {address_key_sql("street_number || ' ' || coalesce(street_direction, '') || ' ' || street_name")}
                AS address_key,
            try_cast(community_area AS INTEGER) AS community_area,
            try_cast(latitude AS DOUBLE) AS lat,
            try_cast(longitude AS DOUBLE) AS lon,
            upper(coalesce(work_description, '')) AS description,
            {
        sql_flags(
            "upper(coalesce(permit_type,'') || ' ' || coalesce(work_type,'') || ' ' || "
            "coalesce(work_description,''))",
            PERMIT_TRADES,
        )
    }
        FROM src
    """)
    con.execute("UPDATE permits SET pin10 = left(pin10, 10)")

    print("build permit_parties")
    unions = " UNION ALL ".join(
        f"SELECT id AS permit_id, {i} AS slot, upper(trim(contact_{i}_type)) AS role_raw, "
        f"upper(trim(contact_{i}_name)) AS name_raw FROM {_csv('permits')} "
        f"WHERE contact_{i}_name IS NOT NULL AND trim(contact_{i}_name) <> ''"
        for i in range(1, 16)
    )
    con.execute(f"""
        CREATE TABLE permit_parties AS
        SELECT *,
            CASE
                WHEN role_raw LIKE '%OWNER AS GENERAL%' THEN 'owner_gc'
                WHEN role_raw LIKE '%GENERAL CONTRACTOR%' THEN 'gc'
                WHEN role_raw LIKE '%ELECTRIC%' THEN 'electrical'
                WHEN role_raw LIKE '%PLUMB%' THEN 'plumbing'
                WHEN role_raw LIKE '%VENTILATION%' OR role_raw LIKE '%REFRIGERATION%' THEN 'hvac'
                WHEN role_raw LIKE '%MASON%' THEN 'masonry'
                WHEN role_raw LIKE '%ARCHITECT%' OR role_raw LIKE '%DESIGN PROFESSIONAL%' THEN 'architect'
                WHEN role_raw LIKE '%ENGINEER%' THEN 'engineer'
                WHEN role_raw LIKE '%OWNER%' THEN 'owner'
                WHEN role_raw LIKE '%EXPEDITOR%' THEN 'expediter'
                WHEN role_raw LIKE '%SIGN%' THEN 'sign'
                WHEN role_raw LIKE '%ELEVATOR%' THEN 'elevator'
                WHEN role_raw LIKE '%WRECK%' OR role_raw LIKE '%DEMOLI%' THEN 'wrecking'
                ELSE 'other'
            END AS role,
            -- name key: strip punctuation and common legal suffixes so variants collapse
            trim(regexp_replace(regexp_replace(name_raw, '[^A-Z0-9 ]', ' ', 'g'),
                '\\b(INC|INCORPORATED|LLC|L L C|CO|CORP|CORPORATION|COMPANY|LTD|LP|L P|THE)\\b', ' ', 'g'))
                AS name_key
        FROM ({unions})
    """)
    con.execute("UPDATE permit_parties SET name_key = trim(regexp_replace(name_key, '\\s+', ' ', 'g'))")

    print("build violations")
    con.execute(f"""
        CREATE TABLE violations AS
        SELECT
            id,
            try_cast(violation_date AS TIMESTAMP)::DATE AS violation_date,
            violation_code,
            violation_status,
            try_cast(violation_status_date AS TIMESTAMP)::DATE AS status_date,
            upper(coalesce(violation_description, '')) AS description,
            inspection_category,
            department_bureau,
            {address_key_sql("address")} AS address_key,
            property_group,
            try_cast(latitude AS DOUBLE) AS lat,
            try_cast(longitude AS DOUBLE) AS lon,
            {sql_flags("upper(coalesce(violation_description,''))", VIOLATION_TRADES)}
        FROM {_csv("violations")}
    """)

    print("build sales")
    con.execute(f"""
        CREATE TABLE sales AS
        SELECT
            lpad(pin, 14, '0') AS pin,
            left(lpad(pin, 14, '0'), 10) AS pin10,
            try_cast(sale_date AS TIMESTAMP)::DATE AS sale_date,
            try_cast(sale_price AS DOUBLE) AS sale_price,
            class,
            left(class, 1) AS major_class,
            deed_type,
            buyer_name,
            seller_name,
            is_multisale = 'true' AS is_multisale,
            (sale_filter_same_sale_within_365 = 'true' OR sale_filter_less_than_10k = 'true'
                OR sale_filter_deed_type = 'true') AS filtered_out
        FROM {_csv("sales")}
    """)

    print("build food_licenses")
    con.execute(f"""
        CREATE TABLE food_licenses AS
        SELECT
            license_id, account_number, legal_name, doing_business_as_name AS dba,
            {address_key_sql("address")} AS address_key,
            try_cast(application_created_date AS TIMESTAMP)::DATE AS application_date,
            try_cast(date_issued AS TIMESTAMP)::DATE AS issue_date,
            try_cast(license_start_date AS TIMESTAMP)::DATE AS start_date
        FROM {_csv("food_licenses")}
    """)

    for t in ("permits", "permit_parties", "violations", "sales", "food_licenses"):
        n = con.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
        print(f"  {t}: {n:,} rows")
    con.close()
    shutil.move(tmp, DB_PATH)
    print(f"wrote {DB_PATH}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("command", choices=["sync", "build"])
    ap.add_argument("--only", nargs="*", help="dataset names for sync")
    args = ap.parse_args()
    if args.command == "sync":
        sync(args.only)
    else:
        build()
    return 0


if __name__ == "__main__":
    sys.exit(main())
