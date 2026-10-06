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

if not RAW.exists():
    raise SystemExit(f"Missing {RAW}. Run explore.py first to download it.")

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
    FROM read_csv('{RAW.as_posix()}')
    WHERE "Property Type" = 'All property types'
      AND "Number of Bedrooms" IN ({bed_list})
      AND Location IN ({county_list}, {city_list})
      AND TRY_CAST(VALUE AS DOUBLE) IS NOT NULL
    """
)
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
    """ % OUT.as_posix()
)
n = con.execute(f"SELECT COUNT(*) FROM read_csv('{OUT.as_posix()}')").fetchone()[0]
print(f"wrote {OUT.relative_to(ROOT)}: {n:,} rows, {OUT.stat().st_size/1024:.0f} KB")
