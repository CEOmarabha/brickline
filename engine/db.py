"""Where the warehouse lives and how the engine and research code open it."""

from __future__ import annotations

from pathlib import Path

import duckdb

DATA = Path("data")
RAW = DATA / "raw"
WAREHOUSE = DATA / "warehouse.duckdb"


def connect(
    path: Path = WAREHOUSE, *, memory_limit: str | None = None, read_only: bool = True
) -> duckdb.DuckDBPyConnection:
    """Open the warehouse, or stop with the command that builds it. `memory_limit` e.g. '8GB'."""
    if not path.exists():
        raise SystemExit(
            f"warehouse missing ({path}): run `uv run python -m engine.warehouse sync` then `... build` first"
        )
    con = duckdb.connect(str(path), read_only=read_only)
    if memory_limit:
        con.execute(f"SET memory_limit = '{memory_limit}'")
    return con
