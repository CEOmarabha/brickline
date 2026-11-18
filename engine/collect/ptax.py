"""Illinois PTAX-203 real estate transfer declarations for Chicago (Illinois Department of Revenue, public domain).

The Cook County Assessor's sales (`sales`) publish about two months behind; the state's transfer declarations
post within days of recording. `ptax_transfers` keeps Chicago declarations recorded since 2021 so the snapshot
can add sales newer than the Assessor's and the two feeds can be reconciled on the months they share
(the recorder document number is in both).

Line codes on the form (PTAX-203 instructions): line 8 property use `A` land, `B` residence, `C` mobile home,
`D` apartments of 6 units or fewer, `E` apartments over 6 units, `F` office, `G` retail, `H` commercial,
`I` industrial, `J` farm, `K` other. Line 10 `b` related parties, `d` court-ordered sale, `e` sale in lieu of
foreclosure, `h` bank REO (the seller is a lender), `l` the buyer is a real estate investment trust.
The data has no phone, email or buyer mailing columns.
"""

from __future__ import annotations

DOMAIN = "illinois-edp.data.socrata.com"
DATASET_ID = "it54-y4c6"
SOURCE_URL = f"https://{DOMAIN}/d/{DATASET_ID}"
SINCE = "2021-01-01"

SELECT = (
    "declaration_id,document_number,date_recorded,line_4_instrument_date,line_1_street,line_1_zip_code,"
    "line_1_township,line_1_primary_pin,line_2_total_parcels,line_3_additional_pins,line_5_instrument_type,"
    "line_6_principal_residence,line_8_current_use,line_8_intended_use,line_10b_sale_between_related,"
    "line_10d_court_ordered_sale,line_10e_sale_in_lieu_of,line_10h_bank_reo,line_10i_auction_sale,"
    "line_10k_seller_buyer_is,line_10l_buyer_is_a_real,line_11_full_consideration,state_exemption,"
    "step_4_buyer_name,step_4_buyer_organization,step_4_seller_name,step_4_seller_organization"
)
WHERE = f"upper(line_1_county) = 'COOK' AND upper(line_1_city) = 'CHICAGO' AND date_recorded >= '{SINCE}T00:00:00'"

# The eight townships of the city (codes 70-77 in the Assessor's sales): Chicago mailing addresses also occur in
# Stickney, Norwood Park and other suburban townships, which the Assessor sync leaves out.
CHICAGO_TOWNSHIPS = (
    "Lake", "Jefferson", "West Chicago", "Lake View", "North Chicago", "Hyde Park", "South Chicago", "Rogers Park"
)  # fmt: skip

# Line 8 use -> the snapshot's investor segments (Assessor classes are used first when the parcel has one).
USE_SEGMENT = {
    "B": "single-family",
    "D": "2-6 unit flat",
    "E": "apartment 7+",
    "F": "commercial/industrial",
    "G": "commercial/industrial",
    "H": "commercial/industrial",
    "I": "commercial/industrial",
}


def build_sql(csv_glob: str) -> str:
    """CREATE TABLE ptax_transfers from the raw CSV pages (one row per declaration)."""
    seg = " ".join(f"WHEN '{k}' THEN '{v}'" for k, v in USE_SEGMENT.items())
    return f"""
        CREATE TABLE ptax_transfers AS
        WITH src AS (
            SELECT * FROM read_csv('{csv_glob}', header=true, all_varchar=true, union_by_name=true)
        )
        SELECT
            declaration_id,
            nullif(trim(document_number), '') AS doc_no,
            try_cast(date_recorded AS TIMESTAMP)::DATE AS recorded_date,
            try_cast(line_4_instrument_date AS TIMESTAMP)::DATE AS instrument_date,
            regexp_replace(trim(line_1_street), '\\s+', ' ', 'g') AS street,
            left(line_1_zip_code, 5) AS zip,
            line_1_township AS township,
            nullif(regexp_replace(coalesce(line_1_primary_pin, ''), '[^0-9]', '', 'g'), '') AS pin,
            left(nullif(regexp_replace(coalesce(line_1_primary_pin, ''), '[^0-9]', '', 'g'), ''), 10) AS pin10,
            try_cast(try_cast(line_2_total_parcels AS DOUBLE) AS INTEGER) AS total_parcels,
            coalesce(line_3_additional_pins = 'true', false) AS additional_pins,
            nullif(trim(line_5_instrument_type), '') AS instrument_type,
            coalesce(line_6_principal_residence = 'true', false) AS principal_residence,
            nullif(trim(line_8_current_use), '') AS current_use,
            nullif(trim(line_8_intended_use), '') AS intended_use,
            CASE coalesce(nullif(trim(line_8_current_use), ''), trim(line_8_intended_use)) {seg} END AS use_segment,
            coalesce(line_10b_sale_between_related = 'true', false) AS related_parties,
            coalesce(line_10d_court_ordered_sale = 'true', false) AS court_ordered,
            coalesce(line_10e_sale_in_lieu_of = 'true', false) AS in_lieu_of_foreclosure,
            coalesce(line_10h_bank_reo = 'true', false) AS bank_reo,
            coalesce(line_10i_auction_sale = 'true', false) AS auction,
            coalesce(line_10k_seller_buyer_is = 'true', false) AS lender_or_government,
            coalesce(line_10l_buyer_is_a_real = 'true', false) AS buyer_is_reit,
            try_cast(line_11_full_consideration AS DOUBLE) AS price,
            nullif(trim(state_exemption), '') AS exemption,
            nullif(trim(coalesce(nullif(trim(step_4_buyer_organization), ''), step_4_buyer_name)), '') AS buyer_name,
            nullif(trim(coalesce(nullif(trim(step_4_seller_organization), ''), step_4_seller_name)), '')
                AS seller_name
        FROM src
        WHERE try_cast(date_recorded AS TIMESTAMP) IS NOT NULL
        QUALIFY row_number() OVER (PARTITION BY declaration_id ORDER BY date_recorded DESC, document_number) = 1
    """
