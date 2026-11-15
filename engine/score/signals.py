"""Shared signal definitions and parcel feature construction.

Used by the backtests (research/backtests) and by the lead snapshot (engine/leads), so a formula that was
validated historically is exactly the formula that scores live leads.
"""

from __future__ import annotations

import duckdb

# Company-style buyer names. Banks, agencies and land trusts are separated out by NON_OPERATOR_RE.
INVESTOR_RE = (
    r"\b(LLC|L L C|INC|CORP|TRUST|PROPERT|HOLDING|INVEST|CAPITAL|REALTY|HOMES|DEVELOP|PARTNERS|FUND|BANK)\b"
)
NON_OPERATOR_RE = (
    r"BANK|MORTGAGE|FEDERAL|SECRETARY|\bHUD\b|FANNIE|FREDDIE|CITY OF|COUNTY|LAND TRUST|TRUST NO|TRUST #"
    r"|CHICAGO TITLE|TRUSTEE|HOUSING AUTH"
)
MAJOR = (
    "(permit_type IN ('PERMIT - NEW CONSTRUCTION', 'PERMIT - RENOVATION/ALTERATION') "
    "AND reported_cost >= 100000)"
)

PARCEL_FEATURES = {
    "sold_365": "recent sale (365d)",
    "investor_sold_365": "recent sale to company/investor buyer (365d)",
    "demo_365": "demolition permit (365d)",
    "violations_365": "any building violation (365d)",
    "violations3_365": "3+ building violations (365d)",
    "vacant_viol_730": "vacant-building / board-up violation (730d)",
    "small_permit_180": "any non-major permit (180d)",
    "major_permit_1095": "major permit already in last 3 years",
}


def q(con: duckdb.DuckDBPyConnection, sql: str) -> list[dict]:
    cur = con.execute(sql)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row, strict=True)) for row in cur.fetchall()]


def one(con: duckdb.DuckDBPyConnection, sql: str) -> dict:
    return q(con, sql)[0]


def prepare_base(con: duckdb.DuckDBPyConnection) -> None:
    """Temp tables: addr_pin (address -> most common parcel) and p (permits with parcel filled in)."""
    con.execute("""
        CREATE OR REPLACE TEMP TABLE addr_pin AS
        SELECT address_key, first(pin10 ORDER BY n DESC, pin10) AS pin10 FROM (
            SELECT address_key, pin10, count(*) AS n FROM permits
            WHERE pin10 IS NOT NULL AND address_key IS NOT NULL GROUP BY ALL
        ) GROUP BY address_key
    """)
    con.execute("""
        CREATE OR REPLACE TEMP TABLE p AS
        SELECT permits.* REPLACE (coalesce(permits.pin10, a.pin10) AS pin10),
               coalesce(permits.pin10, a.pin10, 'A:' || permits.address_key) AS prop
        FROM permits LEFT JOIN addr_pin a USING (address_key)
        WHERE issue_date IS NOT NULL
    """)


def build_parcel_features(con: duckdb.DuckDBPyConnection, snapshots_sql: str) -> None:
    """Create temp table `feat` (one row per snapshot date d × parcel) with PARCEL_FEATURES and target y.

    y = a major permit is applied for at the parcel within 180 days after d (unknown for recent d).
    Requires prepare_base().
    """
    con.execute(f"CREATE OR REPLACE TEMP TABLE snap AS {snapshots_sql}")
    con.execute("""
        CREATE OR REPLACE TEMP TABLE v_pin AS
        SELECT a.pin10, v.violation_date,
               regexp_matches(v.description, 'VACANT|BOARD|SECURE') AS vacant
        FROM violations v JOIN addr_pin a USING (address_key)
    """)
    con.execute("""
        CREATE OR REPLACE TEMP TABLE universe AS
        SELECT DISTINCT pin10 FROM (
          SELECT pin10 FROM permits WHERE pin10 IS NOT NULL UNION ALL SELECT pin10 FROM sales
        )
    """)
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE feat AS
        WITH
        sale_f AS (
          SELECT sn.d, s.pin10, true AS sold_365,
                 bool_or(regexp_matches(upper(coalesce(s.buyer_name,'')), '{INVESTOR_RE}'))
                   AS investor_sold_365
          FROM snap sn JOIN sales s ON s.sale_date > sn.d - INTERVAL 365 DAY AND s.sale_date <= sn.d
          WHERE NOT s.filtered_out GROUP BY ALL
        ),
        perm_f AS (
          SELECT sn.d, p.pin10,
            bool_or(p.permit_type = 'PERMIT - WRECKING/DEMOLITION' AND p.issue_date > sn.d - INTERVAL 365 DAY)
              AS demo_365,
            bool_or(NOT {MAJOR} AND p.issue_date > sn.d - INTERVAL 180 DAY) AS small_permit_180,
            bool_or({MAJOR}) AS major_permit_1095
          FROM snap sn JOIN p ON p.pin10 IS NOT NULL
           AND p.issue_date > sn.d - INTERVAL 1095 DAY AND p.issue_date <= sn.d
          GROUP BY ALL
        ),
        viol_f AS (
          SELECT sn.d, v.pin10,
            count(*) FILTER (WHERE v.violation_date > sn.d - INTERVAL 365 DAY) AS n365,
            bool_or(v.vacant) AS vacant_viol_730
          FROM snap sn JOIN v_pin v ON v.violation_date > sn.d - INTERVAL 730 DAY AND v.violation_date <= sn.d
          GROUP BY ALL
        ),
        target AS (
          SELECT sn.d, p.pin10, true AS y
          FROM snap sn JOIN p ON p.pin10 IS NOT NULL AND {MAJOR}
           AND p.application_date > sn.d AND p.application_date <= sn.d + INTERVAL 180 DAY
          GROUP BY ALL
        )
        SELECT sn.d, u.pin10,
          coalesce(sale_f.sold_365, false) AS sold_365,
          coalesce(sale_f.investor_sold_365, false) AS investor_sold_365,
          coalesce(perm_f.demo_365, false) AS demo_365,
          coalesce(viol_f.n365, 0) >= 1 AS violations_365,
          coalesce(viol_f.n365, 0) >= 3 AS violations3_365,
          coalesce(viol_f.vacant_viol_730, false) AS vacant_viol_730,
          coalesce(perm_f.small_permit_180, false) AS small_permit_180,
          coalesce(perm_f.major_permit_1095, false) AS major_permit_1095,
          coalesce(target.y, false) AS y
        FROM snap sn CROSS JOIN universe u
        LEFT JOIN sale_f ON sale_f.d = sn.d AND sale_f.pin10 = u.pin10
        LEFT JOIN perm_f ON perm_f.d = sn.d AND perm_f.pin10 = u.pin10
        LEFT JOIN viol_f ON viol_f.d = sn.d AND viol_f.pin10 = u.pin10
        LEFT JOIN target ON target.d = sn.d AND target.pin10 = u.pin10
    """)


def fit_combo_rates(con: duckdb.DuckDBPyConnection, train_where: str, m: int = 200) -> float:
    """Create temp table `combo`: shrunk empirical rate per exact feature combination. Returns base rate."""
    base = one(con, f"SELECT avg(y::INT) AS r FROM feat WHERE {train_where}")["r"]
    cols = ", ".join(PARCEL_FEATURES)
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE combo AS
        SELECT {cols}, count(*) AS n, sum(y::INT) AS hits,
               (sum(y::INT) + {m} * {base}) / (count(*) + {m}) AS rate
        FROM feat WHERE {train_where} GROUP BY ALL
    """)
    return base
