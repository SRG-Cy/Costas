"""Export the small slices of data the app needs from the big RTB/CSO download.

Input : data/raw/RIH02.csv        (94 MB, gitignored - run explore.py to download)
Output: reference/rent_area.csv   (small, committed to Git so the app can be deployed)

One row = average monthly rent (EUR) for one half-year, one area (county or one of four
cities), and one bedroom count, for ALL property types. Unpublished cells are dropped.
"""
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "data" / "raw" / "RIH02.csv"
OUT = ROOT / "reference" / "rent_area.csv"

COUNTIES = [
    "Carlow", "Cavan", "Clare", "Cork", "Donegal", "Dublin", "Galway", "Kerry",
    "Kildare", "Kilkenny", "Laois", "Leitrim", "Limerick", "Longford", "Louth",
    "Mayo", "Meath", "Monaghan", "Offaly", "Roscommon", "Sligo", "Tipperary",
    "Waterford", "Westmeath", "Wexford", "Wicklow",
]
# The four cities that Daft's room-rent report also publishes separately.
CITIES = {"Cork City": "Cork", "Galway City": "Galway", "Limerick City": "Limerick", "Waterford City": "Waterford"}
BEDROOMS = ["All bedrooms", "One bed", "Two bed", "Three bed", "Four plus bed"]



def check_rent_area(con) -> None:
    """Fail loudly instead of exporting bad data. Checks the rent_area table before it is written."""
    rows = con.execute("SELECT COUNT(*) FROM rent_area").fetchone()[0]
    if rows == 0:
        raise SystemExit("No published rents found: check the column names and filters against the raw file.")
    # One row per period, area and bedroom count. A duplicate means the filters let two property types through.
    dupes = con.execute(
        "SELECT COUNT(*) FROM (SELECT 1 FROM rent_area GROUP BY half_year, area, bedrooms HAVING COUNT(*) > 1)"
    ).fetchone()[0]
    if dupes:
        raise SystemExit(f"{dupes} duplicate (half_year, area, bedrooms) rows: not exporting.")
    missing = set(COUNTIES) | set(CITIES)
    missing -= {r[0] for r in con.execute("SELECT DISTINCT area FROM rent_area").fetchall()}
    if missing:
        raise SystemExit(f"No rents at all for: {', '.join(sorted(missing))}. Has a place name changed?")


def main(raw: Path = RAW, out: Path = OUT) -> None:
    if not raw.exists():
        raise SystemExit(f"Missing {raw}. Run explore.py first to download it.")

    con = duckdb.connect()
    county_list = ", ".join(f"'{c}'" for c in COUNTIES)
    city_list = ", ".join(f"'{c}'" for c in CITIES)
    bed_list = ", ".join(f"'{b}'" for b in BEDROOMS)

    con.execute(
        f"""
        CREATE TABLE rent_area AS
        SELECT
            HalfYear                                   AS half_year,
            Location                                   AS area,
            CASE WHEN Location IN ({city_list}) THEN 'city' ELSE 'county' END AS area_type,
            "Number of Bedrooms"                       AS bedrooms,
            TRY_CAST(VALUE AS DOUBLE)                  AS rent_eur
        FROM read_csv('{raw.as_posix()}')
        WHERE "Property Type" = 'All property types'
          AND "Number of Bedrooms" IN ({bed_list})
          AND Location IN ({county_list}, {city_list})
          AND TRY_CAST(VALUE AS DOUBLE) IS NOT NULL
        """
    )
    check_rent_area(con)
    # Add the parent county for each city so the app can offer "city or rest of county".
    con.execute(
        "CREATE TABLE city_parent(area VARCHAR, county VARCHAR)"
    )
    con.executemany("INSERT INTO city_parent VALUES (?, ?)", list(CITIES.items()))
    con.execute(
        """
        COPY (
            SELECT r.half_year, r.area, r.area_type,
                   COALESCE(p.county, r.area) AS county,
                   r.bedrooms, r.rent_eur
            FROM rent_area r LEFT JOIN city_parent p USING (area)
            ORDER BY county, area, bedrooms, half_year
        ) TO '%s' (HEADER, DELIMITER ',')
        """ % out.as_posix()
    )
    n = con.execute(f"SELECT COUNT(*) FROM read_csv('{out.as_posix()}')").fetchone()[0]
    print(f"wrote {out.name}: {n:,} rows, {out.stat().st_size/1024:.0f} KB")


if __name__ == "__main__":
    main()
