"""Local analytical warehouse of Chicago / Cook County public records.

    uv run python -m engine.warehouse sync     # download raw CSV pages (resumable)
    uv run python -m engine.warehouse build    # (re)build normalized tables in data/warehouse.duckdb
    uv run python -m engine.warehouse sync --only overture biz_licenses biz_owners   # free contact sources
    uv run python -m engine.warehouse sync --only clerk adu_preapprovals zoning_districts   # round 5 sources

Raw pages are kept under data/raw/<dataset>/ so tables can be rebuilt without re-downloading.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from dataclasses import dataclass

import duckdb

from engine.classify.trades import PERMIT_TRADES, VIOLATION_TRADES, sql_flags
from engine.collect import clerk, hmda, noaa, overture, swdi
from engine.collect.socrata import export_csv
from engine.db import DATA, RAW, WAREHOUSE

DB_PATH = WAREHOUSE

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
    Dataset(
        "biz_license_history",
        CHICAGO,
        "r5kz-chrr",
        "id,license_id,account_number,site_number,legal_name,doing_business_as_name,address,zip_code,"
        "community_area,license_code,license_description,business_activity,application_type,"
        "application_created_date,license_start_date,expiration_date,date_issued,license_status,"
        "license_status_change_date,latitude,longitude",
        "date_issued >= '2014-01-01T00:00:00' OR license_start_date >= '2014-01-01T00:00:00'",
    ),
    Dataset(
        "food_inspections",
        CHICAGO,
        "4ijn-s7e5",
        "inspection_id,dba_name,license_,facility_type,risk,address,inspection_date,inspection_type,results,"
        "violations,latitude,longitude",
        "inspection_date >= '2016-01-01T00:00:00'",
    ),
    Dataset(
        "parcel_addresses",
        COOK,
        "3723-97qp",
        "pin,pin10,year,prop_address_full,prop_address_zipcode_1,owner_address_name,owner_address_full,"
        "owner_address_city_name,owner_address_state,owner_address_zipcode_1",
        "year = 2026 AND prop_address_city_name = 'CHICAGO'",
    ),
    Dataset(
        "biz_licenses",
        CHICAGO,
        "uupf-x98q",
        "license_id,account_number,site_number,legal_name,doing_business_as_name,address,zip_code,community_area,"
        "license_description,business_activity,license_status,expiration_date,latitude,longitude",
    ),
    Dataset(
        "biz_owners",
        CHICAGO,
        "ezma-pppn",
        "account_number,doing_business_as_name,owner_first_name,owner_middle_initial,owner_last_name,"
        "owner_name_suffix,owner_name,owner_title",
    ),
    # Applicant names and mailing addresses are deliberately not selected: only the property and the request.
    Dataset(
        "adu_preapprovals",
        CHICAGO,
        "j4h8-ug9m",
        "id,submission_date,status,action_date,address,street_number,street_direction,street_name,zip,ward,zoning,"
        "latitude,longitude,coach_house,conversion_unit,principal_building_built_year,dwelling_units_in_lot,"
        "max_number_of_adu_allowed,max_number_coach_house_units_allowed,adu_applying_for,"
        "number_affordable_units_required,property_owner_occupied",
    ),
    # Today's zoning map without geometry: zone_class per polygon plus the application number (`ordinance`),
    # passage date (`ordinance_1`) and Clerk record number (`clerk_docn`) of the change that created it.
    Dataset(
        "zoning_districts",
        CHICAGO,
        "dj47-wfun",
        "case_numbe,case_type,zoning_id,zone_type,zone_class,create_dat,edit_date,pd_prefix,pd_num,ordinance,"
        "ordinance_1,clerk_docn,zoning_rel,shape_area",
    ),
    Dataset("community_areas", CHICAGO, "igwz-8jzy", "area_numbe,community,the_geom"),
    Dataset("tracts_2010", CHICAGO, "74p9-q2aq", "geoid10,commarea,the_geom"),
    Dataset("tracts_2020", CHICAGO, "7qjk-677h", "tract_fips,tract_ce,commarea,the_geom"),
    Dataset(
        "sr311",
        CHICAGO,
        "v6vf-nfxy",
        "sr_number,sr_type,status,created_date,closed_date,street_address,zip_code,community_area,latitude,longitude,"
        "duplicate",
        "created_date >= '2015-01-01T00:00:00' AND sr_type in("
        + ",".join(
            f"'{t}'"
            for t in (
                "Building Violation",
                "Water in Basement Complaint",
                "No Building Permit and Construction Violation",
                "Buildings - Plumbing Violation",
                "Vacant/Abandoned Building Complaint",
                "Water Lead Test Kit Request",
                "Sewer Cave-In Inspection Request",
                "Porch Inspection Request",
                "Tree Emergency",
                "Rodent Baiting/Rat Complaint",
            )
        )
        + ")",
    ),
    Dataset(
        "benchmarking",
        CHICAGO,
        "xq83-jr8c",
        "data_year,id,property_name,address,community_area,primary_property_type,gross_floor_area_buildings_sq_ft,"
        "year_built,energy_star_score,site_eui_kbtu_sq_ft,chicago_energy_rating,latitude,longitude",
    ),
    Dataset(
        "res_chars",
        COOK,
        "x54s-btds",
        "pin,class,char_yrblt,char_bldg_sf,char_type_resd,char_ext_wall,char_roof_cnst,char_air,char_heat,char_bsmt,"
        "char_repair_cnd,char_porch,char_use,char_apts",
        "year = 2026 AND township_code in(" + ",".join(f"'{t}'" for t in CHICAGO_TOWNSHIPS) + ")",
    ),
]

# Flags on the free-text violations of a food inspection (upper-cased). RE2 syntax. Each cited item reads
# "<n>. <HEADING> - Comments: <inspector text>"; two generic headings are removed first because they name a
# topic the item is usually not about (rodent-proof garbage containers; hand-washing supplies).
FOOD_TEXT_NEUTRALIZE = (
    "OUTSIDE GARBAGE WASTE GREASE AND STORAGE AREA; CLEAN, RODENT PROOF, ALL CONTAINERS COVERED",
    "ADEQUATE HANDWASHING SINKS PROPERLY SUPPLIED AND ACCESSIBLE",
)
FOOD_VIOLATION_FLAGS: dict[str, str] = {
    "pest": r"RODENT|\bMICE\b|\bMOUSE\b|\bRATS?\b|ROACH|INSECT|\bPESTS?\b|DROPPINGS|\bFLIES\b|VERMIN",
    "plumbing": r"PLUMBING|LEAK|SEWAGE|\bDRAIN|HAND ?SINK|BACKFLOW|WASTE ?WATER",
    "plumbing_strict": r"PLUMBING|LEAK|SEWAGE|\bDRAIN|BACKFLOW|WASTE ?WATER",
    "ventilation": r"VENTILATION|\bHOODS?\b|EXHAUST|\bDUCTS?\b",
    "hood": r"\bHOODS?\b|EXHAUST|\bDUCTS?\b",
    "cleaning": r"SANITI[ZS]|CLEANED|CLEANING|\bUNCLEAN|\bDIRT|GREASE|FOOD-CONTACT SURFACES|\bCLEAN\b",
}


def food_text_sql(expr: str) -> str:
    out = expr
    for phrase in FOOD_TEXT_NEUTRALIZE:
        out = f"replace({out}, '{phrase}', '')"
    return out


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


NON_SOCRATA_SOURCES = ("clerk", "noaa", "hmda", "swdi", "overture")
SOURCE_NAMES = (*(ds.name for ds in DATASETS), *NON_SOCRATA_SOURCES)


def sync(names: list[str] | None = None) -> None:
    unknown = sorted(set(names or []) - set(SOURCE_NAMES))
    if unknown:
        raise SystemExit(f"unknown source(s) {', '.join(unknown)}; choose from: {', '.join(SOURCE_NAMES)}")
    for ds in DATASETS:
        if names and ds.name not in names:
            continue
        print(f"sync {ds.name} ({ds.domain}/{ds.dataset_id})")
        export_csv(ds.domain, ds.dataset_id, ds.select, ds.where, RAW / ds.name)
    if not names or "clerk" in names:
        print("sync City Clerk zoning reclassification ordinances")
        clerk.sync(RAW / "clerk")
    if not names or "noaa" in names:
        print("sync noaa storm events")
        noaa.sync(RAW / "noaa")
    if not names or "hmda" in names:
        print("sync hmda home-improvement loans")
        hmda.sync(RAW / "hmda")
    if not names or "swdi" in names:
        print("sync swdi hail detections")
        swdi.sync(RAW / "swdi")
    if not names or "overture" in names:
        print("sync overture places (Chicago metro)")
        overture.sync(RAW / "overture")


def _csv(name: str) -> str:
    return f"read_csv('{RAW / name}/page-*.csv', header=true, all_varchar=true, union_by_name=true)"


def missing_raw() -> list[str]:
    """Raw inputs `build` reads that `sync` has not downloaded yet."""
    wanted = {ds.name: "page-*.csv" for ds in DATASETS}
    wanted |= {
        "noaa": "storms-*.csv",
        "hmda": "hmda-*.csv",
        "swdi": "nx3hail-*.csv",
        "overture": "places-*.parquet",
    }
    return sorted(name for name, pattern in wanted.items() if not list((RAW / name).glob(pattern)))


def build() -> None:
    missing = missing_raw()
    if missing:
        raise SystemExit(
            f"raw data missing for: {', '.join(missing)}; run `uv run python -m engine.warehouse sync` first"
        )
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

    print("build biz_license_history")
    # Address ranges keep their first number; home-based licenses carry a redacted address.
    lic_address_key = address_key_sql(r"regexp_replace(address, '^(\d+)-\d+', '\1')")
    con.execute(f"""
        CREATE TABLE biz_license_history AS
        SELECT try_cast(id AS VARCHAR) AS row_id, license_id, account_number,
            try_cast(site_number AS INTEGER) AS site_number,
            legal_name, doing_business_as_name AS dba, address,
            CASE WHEN address LIKE '%REDACTED%' THEN NULL ELSE {lic_address_key} END AS address_key,
            zip_code AS zip, try_cast(community_area AS INTEGER) AS community_area,
            try_cast(license_code AS INTEGER) AS license_code, license_description, business_activity,
            application_type,
            try_cast(application_created_date AS TIMESTAMP)::DATE AS application_date,
            try_cast(license_start_date AS TIMESTAMP)::DATE AS start_date,
            try_cast(expiration_date AS TIMESTAMP)::DATE AS expiration_date,
            try_cast(date_issued AS TIMESTAMP)::DATE AS issue_date,
            license_status,
            try_cast(license_status_change_date AS TIMESTAMP)::DATE AS status_change_date,
            try_cast(latitude AS DOUBLE) AS lat, try_cast(longitude AS DOUBLE) AS lon
        FROM {_csv("biz_license_history")}
    """)

    print("build food_inspections")
    # Address ranges ("5242-5244 W NORTH AVE") keep their first number so they parse like every other source.
    insp_address_key = address_key_sql(r"regexp_replace(address, '^(\d+)-\d+', '\1')")
    con.execute(f"""
        CREATE TABLE food_inspections AS
        WITH src AS (
            SELECT inspection_id, dba_name, license_, facility_type, risk, address,
                try_cast(inspection_date AS TIMESTAMP)::DATE AS inspection_date,
                inspection_type, results, upper(coalesce(violations, '')) AS violations,
                try_cast(latitude AS DOUBLE) AS lat, try_cast(longitude AS DOUBLE) AS lon
            FROM {_csv("food_inspections")}
        )
        SELECT
            try_cast(inspection_id AS BIGINT) AS inspection_id,
            dba_name AS dba,
            try_cast(license_ AS BIGINT) AS license_no,
            facility_type, risk,
            {insp_address_key} AS address_key,
            inspection_date, inspection_type, results, violations, lat, lon,
            {sql_flags(food_text_sql("violations"), FOOD_VIOLATION_FLAGS, prefix="f_")}
        FROM src
        WHERE inspection_date IS NOT NULL
        QUALIFY row_number() OVER (
            PARTITION BY inspection_id ORDER BY inspection_date, results, dba, violations) = 1
    """)

    print("build parcels")
    con.execute(f"""
        CREATE TABLE parcels AS
        SELECT pin10,
            arg_max(prop_address_full, pin) AS address,
            {address_key_sql("arg_max(prop_address_full, pin)")} AS address_key,
            arg_max(prop_address_zipcode_1, pin) AS zip,
            arg_max(owner_address_name, pin) AS owner_name,
            arg_max(owner_address_full || ', ' || coalesce(owner_address_city_name, '') || ' '
                    || coalesce(owner_address_state, '') || ' ' || coalesce(owner_address_zipcode_1, ''), pin)
                AS owner_mailing,
            count(*) AS units
        FROM {_csv("parcel_addresses")}
        WHERE pin10 IS NOT NULL
        GROUP BY pin10
    """)

    print("build community_areas")
    con.execute(f"""
        CREATE TABLE community_areas AS
        SELECT try_cast(area_numbe AS INTEGER) AS community_area,
            array_to_string(list_transform(string_split(lower(community), ' '),
                lambda w: upper(w[1]) || w[2:]), ' ') AS name,
            the_geom AS geom_wkt
        FROM {_csv("community_areas")}
    """)

    print("build sr311")
    con.execute(f"""
        CREATE TABLE sr311 AS
        SELECT sr_number, sr_type, status,
            try_cast(created_date AS TIMESTAMP)::DATE AS created_date,
            try_cast(closed_date AS TIMESTAMP)::DATE AS closed_date,
            {address_key_sql("street_address")} AS address_key,
            zip_code, try_cast(community_area AS INTEGER) AS community_area,
            try_cast(latitude AS DOUBLE) AS lat, try_cast(longitude AS DOUBLE) AS lon,
            coalesce(duplicate, 'false') = 'true' AS duplicate
        FROM {_csv("sr311")}
    """)

    print("build benchmarking")
    con.execute(f"""
        CREATE TABLE benchmarking AS
        SELECT try_cast(data_year AS INTEGER) AS data_year, id AS building_id, property_name,
            {address_key_sql("address")} AS address_key, address, community_area, primary_property_type,
            try_cast(gross_floor_area_buildings_sq_ft AS DOUBLE) AS floor_area,
            try_cast(year_built AS INTEGER) AS year_built,
            try_cast(energy_star_score AS DOUBLE) AS energy_star_score,
            try_cast(site_eui_kbtu_sq_ft AS DOUBLE) AS site_eui,
            try_cast(chicago_energy_rating AS DOUBLE) AS energy_rating,
            try_cast(latitude AS DOUBLE) AS lat, try_cast(longitude AS DOUBLE) AS lon
        FROM {_csv("benchmarking")}
    """)

    print("build res_chars")
    con.execute(f"""
        CREATE TABLE res_chars AS
        SELECT left(lpad(pin, 14, '0'), 10) AS pin10,
            first(class ORDER BY pin, class NULLS LAST) AS class,
            min(try_cast(try_cast(char_yrblt AS DOUBLE) AS INTEGER)) AS year_built,
            sum(try_cast(char_bldg_sf AS DOUBLE)) AS bldg_sf,
            first(char_type_resd ORDER BY pin, char_type_resd NULLS LAST) AS type_resd,
            first(char_ext_wall ORDER BY pin, char_ext_wall NULLS LAST) AS ext_wall,
            first(char_roof_cnst ORDER BY pin, char_roof_cnst NULLS LAST) AS roof,
            first(char_air ORDER BY pin, char_air NULLS LAST) AS air,
            first(char_heat ORDER BY pin, char_heat NULLS LAST) AS heat,
            first(char_bsmt ORDER BY pin, char_bsmt NULLS LAST) AS basement,
            first(char_repair_cnd ORDER BY pin, char_repair_cnd NULLS LAST) AS repair_condition,
            first(char_porch ORDER BY pin, char_porch NULLS LAST) AS porch,
            first(char_use ORDER BY pin, char_use NULLS LAST) AS use,
            first(char_apts ORDER BY pin, char_apts NULLS LAST) AS apts
        FROM {_csv("res_chars")}
        GROUP BY 1
    """)

    print("build storms")
    con.execute(f"""
        CREATE TABLE storms AS
        SELECT event_id, strptime(begin_date_time, '%d-%b-%y %H:%M:%S')::DATE AS event_date, event_type,
            try_cast(magnitude AS DOUBLE) AS magnitude, try_cast(lat AS DOUBLE) AS lat,
            try_cast(lon AS DOUBLE) AS lon, location, damage_property
        FROM read_csv('{RAW / "noaa"}/storms-*.csv', header=true, all_varchar=true, union_by_name=true)
    """)

    print("build tracts")
    con.execute(f"""
        CREATE TABLE tracts AS
        SELECT 2010 AS vintage, geoid10 AS geoid, try_cast(commarea AS INTEGER) AS community_area,
            the_geom AS geom_wkt FROM {_csv("tracts_2010")}
        UNION ALL
        SELECT 2020, tract_fips || tract_ce, try_cast(commarea AS INTEGER), the_geom
        FROM {_csv("tracts_2020")}
    """)

    print("build hmda_home_improvement")
    con.execute(f"""
        CREATE TABLE hmda_home_improvement AS
        SELECT try_cast(activity_year AS INTEGER) AS year, census_tract AS tract,
            try_cast(loan_amount AS DOUBLE) AS loan_amount, occupancy_type, total_units,
            "open-end_line_of_credit" AS open_end, business_or_commercial_purpose AS business_purpose,
            lien_status, try_cast(income AS DOUBLE) AS income_k, derived_dwelling_category AS dwelling
        FROM read_csv('{RAW / "hmda"}/hmda-*.csv', header=true, all_varchar=true, union_by_name=true)
        WHERE census_tract IS NOT NULL AND census_tract <> 'NA'
    """)

    print("build hail_cells")
    con.execute(f"""
        CREATE TABLE hail_cells AS
        SELECT strptime(ztime, '%Y-%m-%dT%H:%M:%SZ') AS ts,
            (strptime(ztime, '%Y-%m-%dT%H:%M:%SZ') - INTERVAL 6 HOUR)::DATE AS local_date,
            wsr_id AS radar, cell_id,
            try_cast(prob AS INTEGER) AS prob, try_cast(sevprob AS INTEGER) AS sevprob,
            try_cast(maxsize AS DOUBLE) AS max_size_in,
            try_cast(lat AS DOUBLE) AS lat, try_cast(lon AS DOUBLE) AS lon
        FROM read_csv('{RAW / "swdi"}/nx3hail-*.csv', header=true, all_varchar=true, union_by_name=true)
    """)

    print("build places")
    chi_lat0, chi_lat1, chi_lon0, chi_lon1 = overture.CHICAGO_BBOX
    con.execute(f"""
        CREATE TABLE places AS
        SELECT id, name, category, categories, phones, websites, emails, address, locality, postcode, region,
            confidence, status, lat, lon,
            lat BETWEEN {chi_lat0} AND {chi_lat1} AND lon BETWEEN {chi_lon0} AND {chi_lon1}
                AND (upper(locality) = 'CHICAGO' OR (locality IS NULL AND postcode LIKE '606%'))
                AS in_chicago,
            release
        FROM read_parquet('{RAW / "overture"}/places-*.parquet')
    """)

    print("build biz_licenses")
    con.execute(f"""
        CREATE TABLE biz_licenses AS
        SELECT license_id, account_number, try_cast(site_number AS INTEGER) AS site_number,
            legal_name, doing_business_as_name AS dba, address, {address_key_sql("address")} AS address_key,
            zip_code AS zip, try_cast(community_area AS INTEGER) AS community_area,
            license_description, business_activity, license_status,
            try_cast(expiration_date AS TIMESTAMP)::DATE AS expiration_date,
            try_cast(latitude AS DOUBLE) AS lat, try_cast(longitude AS DOUBLE) AS lon
        FROM {_csv("biz_licenses")}
    """)

    print("build adu_preapprovals")
    con.execute(f"""
        CREATE TABLE adu_preapprovals AS
        SELECT id AS adu_id,
            try_cast(submission_date AS TIMESTAMP)::DATE AS submitted_date,
            try_cast(action_date AS TIMESTAMP)::DATE AS action_date,
            status,
            {address_key_sql("address")} AS address_key, address,
            try_cast(ward AS INTEGER) AS ward, zoning,
            try_cast(latitude AS DOUBLE) AS lat, try_cast(longitude AS DOUBLE) AS lon,
            try_cast(coach_house AS BOOLEAN) AS coach_house,
            try_cast(conversion_unit AS BOOLEAN) AS conversion_unit,
            try_cast(principal_building_built_year AS INTEGER) AS year_built,
            try_cast(dwelling_units_in_lot AS INTEGER) AS units_on_lot,
            try_cast(max_number_of_adu_allowed AS INTEGER) AS max_adus,
            try_cast(adu_applying_for AS INTEGER) AS adus_applied
        FROM {_csv("adu_preapprovals")}
        WHERE try_cast(submission_date AS TIMESTAMP) IS NOT NULL
    """)

    print("build zoning_districts")
    con.execute(f"""
        CREATE TABLE zoning_districts AS
        SELECT try_cast(zoning_id AS INTEGER) AS zoning_id, zone_class,
            try_cast(zone_type AS INTEGER) AS zone_type,
            upper(nullif(trim(ordinance), '')) AS app_no,
            try_cast(try_cast(ordinance_1 AS TIMESTAMP) AS DATE) AS ordinance_date,
            nullif(trim(clerk_docn), '') AS clerk_docn,
            try_cast(try_cast(create_dat AS TIMESTAMP) AS DATE) AS created,
            try_cast(shape_area AS DOUBLE) AS area,
            try_cast(pd_num AS INTEGER) AS pd_num
        FROM {_csv("zoning_districts")}
    """)

    zoning_json = clerk.write_flat(RAW / "clerk") if (RAW / "clerk" / "list").exists() else None
    if zoning_json:
        print("build zoning_changes")
        con.execute(f"""
            CREATE TABLE zoning_changes AS
            SELECT matter_id, record_no, file_year, title,
                try_cast(intro_date AS DATE) AS intro_date,
                try_cast(final_action_date AS DATE) AS final_action_date,
                status, sub_status,
                sub_status IN ('Passed', 'Passed as Substitute') AS passed,
                CASE WHEN sub_status IN ('Passed', 'Passed as Substitute')
                     THEN try_cast(final_action_date AS DATE) END AS passed_date,
                sponsor, committee, map_no, app_no, type1, planned_development, from_district, to_district,
                addr_idx::INTEGER AS addr_idx, try_cast(addr_num AS INTEGER) AS addr_num,
                try_cast(addr_num_to AS INTEGER) AS addr_num_to, addr_dir, addr_street,
                CASE WHEN addr_text IS NULL THEN NULL ELSE {address_key_sql("addr_text")} END AS address_key
            FROM read_json('{zoning_json}', format='newline_delimited', sample_size=-1,
                columns={{matter_id: 'VARCHAR', record_no: 'VARCHAR', file_year: 'INTEGER', title: 'VARCHAR',
                    intro_date: 'VARCHAR', final_action_date: 'VARCHAR', status: 'VARCHAR',
                    sub_status: 'VARCHAR', legacy_status: 'VARCHAR', sponsor: 'VARCHAR',
                    committee: 'VARCHAR', map_no: 'VARCHAR', app_no: 'VARCHAR', type1: 'BOOLEAN',
                    planned_development: 'BOOLEAN', from_district: 'VARCHAR', to_district: 'VARCHAR',
                    addr_idx: 'INTEGER', addr_num: 'INTEGER', addr_num_to: 'INTEGER', addr_dir: 'VARCHAR',
                    addr_street: 'VARCHAR', addr_text: 'VARCHAR'}})
        """)

    print("build biz_owners")
    con.execute(f"""
        CREATE TABLE biz_owners AS
        SELECT account_number, doing_business_as_name AS dba,
            nullif(trim(owner_first_name), '') AS first_name,
            nullif(trim(owner_middle_initial), '') AS middle,
            nullif(trim(owner_last_name), '') AS last_name, nullif(trim(owner_name_suffix), '') AS suffix,
            nullif(trim(owner_name), '') AS entity_name, nullif(trim(owner_title), '') AS title
        FROM {_csv("biz_owners")}
    """)

    for t in (
        "permits",
        "permit_parties",
        "violations",
        "sales",
        "food_licenses",
        "biz_license_history",
        "food_inspections",
        "parcels",
        "community_areas",
        "sr311",
        "benchmarking",
        "res_chars",
        "storms",
        "tracts",
        "hmda_home_improvement",
        "hail_cells",
        "places",
        "biz_licenses",
        "biz_owners",
        "adu_preapprovals",
        "zoning_districts",
        *(["zoning_changes"] if zoning_json else []),
    ):
        n = con.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
        print(f"  {t}: {n:,} rows")
    con.close()
    shutil.move(tmp, DB_PATH)
    print(f"wrote {DB_PATH}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("command", choices=["sync", "build"])
    ap.add_argument("--only", nargs="*", help="sources to sync (default: all)")
    args = ap.parse_args()
    if args.command == "sync":
        sync(args.only)
    else:
        build()
    return 0


if __name__ == "__main__":
    sys.exit(main())
