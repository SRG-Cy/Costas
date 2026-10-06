"""Load the CSO/RTB rent table (RIH02) into a clean DuckDB table.

Run from anywhere:  python load_rent.py
Input : data/raw/RIH02.csv        (raw download, never edited)
Output: data/costas.duckdb        (table: rent)
"""
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent
RAW_CSV = ROOT / "data" / "raw" / "RIH02.csv"
DB_PATH = ROOT / "data" / "costas.duckdb"

if not RAW_CSV.exists():
    raise SystemExit(f"Missing {RAW_CSV}. Run explore.py first to download it.")

con = duckdb.connect(str(DB_PATH))

# One row = average monthly rent (EUR) for one half-year, one location,
# one bedroom count and one property type. Empty VALUE = RTB did not
# publish that cell, so we keep it as NULL (it is NOT zero).
con.execute(
    f"""
    CREATE OR REPLACE TABLE rent AS
    SELECT
        HalfYear                              AS half_year,      -- e.g. '2025H2'
        CAST(left(HalfYear, 4) AS INTEGER)    AS year,
        CAST(right(HalfYear, 1) AS INTEGER)   AS half,           -- 1 or 2
        "Number of Bedrooms"                  AS bedrooms,
        "Property Type"                       AS property_type,
        C03004V03625                          AS location_code,
        Location                              AS location,
        TRY_CAST(VALUE AS DOUBLE)             AS rent_eur
    FROM read_csv('{RAW_CSV.as_posix()}')
    """
)

# --- Basic data checks: fail loudly instead of silently loading bad data ---
total, published = con.execute("SELECT COUNT(*), COUNT(rent_eur) FROM rent").fetchone()
print(f"rows: {total:,}   rows with a published rent: {published:,}")
assert total > 0, "rent table is empty"
assert published > 0, "no rent values parsed - check the VALUE column"

# The natural key should be unique: one row per period/location/bedrooms/type.
dupes = con.execute(
    """
    SELECT COUNT(*) FROM (
        SELECT half_year, location_code, bedrooms, property_type
        FROM rent GROUP BY ALL HAVING COUNT(*) > 1
    )
    """
).fetchone()[0]
assert dupes == 0, f"{dupes} duplicate keys found"

print(con.sql("SELECT MIN(half_year) AS first, MAX(half_year) AS last FROM rent"))
print(con.sql("DESCRIBE rent"))
con.close()
