from pathlib import Path
import duckdb

ROOT = Path(__file__).resolve().parent
RAW_CSV = ROOT / "data" / "raw" / "RIH02.csv"
DB_PATH = ROOT / "data" / "costas.duckdb"

COUNTY_NAMES = [
    "Carlow",
    "Cavan",
    "Clare",
    "Cork",
    "Donegal",
    "Dublin",
    "Galway",
    "Kerry",
    "Kildare",
    "Kilkenny",
    "Laois",
    "Leitrim",
    "Limerick",
    "Longford",
    "Louth",
    "Mayo",
    "Meath",
    "Monaghan",
    "Offaly",
    "Roscommon",
    "Sligo",
    "Tipperary",
    "Waterford",
    "Westmeath",
    "Wexford",
    "Wicklow",
]

con = duckdb.connect(str(DB_PATH))

placeholders = ", ".join("?" for _ in COUNTY_NAMES)

for location, rent in con.execute(
    f"""
    select location, rent_eur as rent
    from rent
    where location IN ({placeholders})
    and bedrooms = 'All bedrooms'
    and property_type = 'All property types'
    and half_year = (SELECT MAX(half_year) FROM rent)
    order by rent asc
    """,
    COUNTY_NAMES,).fetchall():
    print(f"{location:10s} €{rent:,.0f}")



