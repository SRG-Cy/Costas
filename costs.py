"""Cost calculation for the newcomer cost-of-living estimator.

No UI code here: every function takes plain values and returns plain data, so it can be
tested. All numbers come from the CSV files in reference/ - nothing is invented.

  rent_area.csv     RTB/CSO average monthly rent by county and four cities (whole homes)
  rooms.csv         Daft.ie Rental Report 2026Q1, average listed room rents
  county_market.csv which room-rent market each county belongs to
  catalogue.csv     curated costs, each with a source, date and confidence
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import duckdb

REF = Path(__file__).resolve().parent / "reference"
BEDROOM_OPTIONS = ["One bed", "Two bed", "Three bed", "Four plus bed"]


def _rows(sql: str, params: list | None = None) -> list[tuple]:
    con = duckdb.connect()
    try:
        return con.execute(sql, params or []).fetchall()
    finally:
        con.close()


def _csv(name: str) -> str:
    return f"read_csv('{(REF / name).as_posix()}', header=true, all_varchar=true)"


# ---------------------------------------------------------------- lookups
def counties() -> list[str]:
    return [r[0] for r in _rows(f"SELECT county FROM {_csv('county_market.csv')} ORDER BY county")]


def city_option(county: str) -> str | None:
    """Name of the city in this county that has its own published figures, if any."""
    rows = _rows(f"SELECT city_room_market FROM {_csv('county_market.csv')} WHERE county = ?", [county])
    return rows[0][0] if rows and rows[0][0] else None


def latest_period() -> str:
    return _rows(f"SELECT MAX(half_year) FROM {_csv('rent_area.csv')}")[0][0]


def own_place_rent(county: str, bedrooms: str, in_city: bool = False) -> dict | None:
    """Latest RTB average monthly rent for a whole home. Falls back to the county."""
    city = city_option(county) if in_city else None
    for area, note in ([(city, "")] if city else []) + [(county, f"No published {city} figure, so the county average is shown." if city else "")]:
        rows = _rows(
            f"""SELECT half_year, TRY_CAST(rent_eur AS DOUBLE) FROM {_csv('rent_area.csv')}
                WHERE area = ? AND bedrooms = ? AND rent_eur <> ''
                ORDER BY half_year DESC LIMIT 1""",
            [area, bedrooms],
        )
        if rows:
            return {"rent": rows[0][1], "period": rows[0][0], "area": area, "note": note,
                    "source": "RTB Rent Index via CSO table RIH02 (average of registered tenancies)"}
    return None


def room_market(county: str, in_city: bool = False) -> str:
    rows = _rows(f"SELECT room_market, city_room_market FROM {_csv('county_market.csv')} WHERE county = ?", [county])
    region, city = rows[0]
    return city if (in_city and city) else region


def room_rent(county: str, room_type: str, dwelling: str, ensuite: bool, in_city: bool = False) -> dict | None:
    """Average listed room rent (Daft.ie 2026Q1). Substitutes a nearby room type if unpublished."""
    market = room_market(county, in_city)
    want = (room_type, dwelling, "yes" if ensuite else "no")
    candidates = [want, (room_type, "house", "no"), ("double", "house", "no")]
    seen = []
    for cand in candidates:
        if cand in seen:
            continue
        seen.append(cand)
        rows = _rows(
            f"""SELECT TRY_CAST(avg_listed_rent_eur AS DOUBLE), quarter, source_page
                FROM {_csv('rooms.csv')}
                WHERE market = ? AND room_type = ? AND dwelling = ? AND ensuite = ?
                  AND avg_listed_rent_eur <> ''""",
            [market, *cand],
        )
        if rows:
            note = ""
            if cand != want:
                note = (f"Too few listings were published for a {want[0]} room in a {want[1]}"
                        f"{' with' if want[2]=='yes' else ', no'} ensuite in {market}, "
                        f"so the figure for a {cand[0]} room in a {cand[1]}"
                        f"{' with' if cand[2]=='yes' else ', no'} ensuite is shown.")
            return {"rent": rows[0][0], "period": rows[0][1], "market": market, "note": note,
                    "source": f"Daft.ie Rental Report 2026Q1, page {rows[0][2]} (average listed rent)",
                    "chosen": cand}
    return None


def catalogue() -> list[dict]:
    cols = ["item_id", "category", "label", "applies_to", "monthly_eur_low", "monthly_eur_high",
            "status", "source_name", "source_url", "as_of", "confidence", "notes"]
    rows = _rows(f"SELECT {', '.join(cols)} FROM {_csv('catalogue.csv')}")
    out = []
    for r in rows:
        d = dict(zip(cols, r))
        for k in ("monthly_eur_low", "monthly_eur_high"):
            d[k] = float(d[k]) if d[k] not in (None, "") else None
        out.append(d)
    return out


def catalogue_item(item_id: str) -> dict | None:
    return next((c for c in catalogue() if c["item_id"] == item_id), None)


def rent_history(area: str, bedrooms: str) -> list[tuple[str, float]]:
    return [(r[0], r[1]) for r in _rows(
        f"""SELECT half_year, TRY_CAST(rent_eur AS DOUBLE) FROM {_csv('rent_area.csv')}
            WHERE area = ? AND bedrooms = ? AND rent_eur <> '' ORDER BY half_year""", [area, bedrooms])]


def own_place_by_county(bedrooms: str) -> list[tuple[str, float]]:
    return [(r[0], r[1]) for r in _rows(
        f"""SELECT area, TRY_CAST(rent_eur AS DOUBLE) FROM {_csv('rent_area.csv')}
            WHERE area_type = 'county' AND bedrooms = ? AND half_year = (SELECT MAX(half_year) FROM {_csv('rent_area.csv')})
              AND rent_eur <> '' ORDER BY 2""", [bedrooms])]


def essentials_basket(persona: str, own_place: bool) -> list[tuple[str, float, str]]:
    """Everyday costs by category for a student or a working professional.

    Figures are the author's own experience of living in Galway for three years. Where no figure was given
    (professional health insurance) the official MESL share is used. A whole home uses a sourced electricity
    average, and adds broadband. Gas and heating are not included yet.
    """
    col = "student_eur" if persona == "student" else "professional_eur"
    mesl = dict(mesl_breakdown())
    out = []
    for cat, val, own_only, own_item, mesl_cat, note in _rows(
            f"""SELECT category, TRY_CAST({col} AS DOUBLE), own_place_only, own_place_catalogue_item,
                       mesl_category, note FROM {_csv('essentials_basket.csv')}"""):
        if own_only == "yes" and not own_place:
            continue
        if own_place and own_item:
            val = float(catalogue_item(own_item)["monthly_eur_low"])
        elif val is None:
            val = mesl[mesl_cat]
        out.append((cat, round(val, 2), note))
    return out


def mesl_breakdown() -> list[tuple[str, float]]:
    """Split of the 2025 MESL essentials figure by category.

    MESL 2025 publishes the total (EUR 287 a week) but not the category split for a single adult, so we apply
    the shares from the published 2024 budget to the 2025 total. Shares, not 2024 prices: the result sums to the
    figure the app uses for everyday essentials.
    """
    rows = _rows(f"SELECT category, TRY_CAST(weekly_eur_2024 AS DOUBLE) FROM {_csv('mesl_breakdown.csv')}")
    total_2024 = sum(r[1] for r in rows)
    monthly = catalogue_item("mesl_single_urban")["monthly_eur_low"]
    return [(r[0], round(r[1] / total_2024 * monthly, 2)) for r in rows]


def room_source_url() -> str:
    rows = _rows(f"SELECT source_url FROM {_csv('rooms.csv')} LIMIT 1")
    return rows[0][0] if rows else ""


def rooms_by_market(room_type: str, dwelling: str, ensuite: bool) -> list[tuple[str, float]]:
    return [(r[0], r[1]) for r in _rows(
        f"""SELECT market, TRY_CAST(avg_listed_rent_eur AS DOUBLE) FROM {_csv('rooms.csv')}
            WHERE room_type = ? AND dwelling = ? AND ensuite = ? AND avg_listed_rent_eur <> '' ORDER BY 2""",
        [room_type, dwelling, "yes" if ensuite else "no"])]


# ---------------------------------------------------------------- estimate
@dataclass
class Choices:
    county: str
    housing: str                     # "room" or "own_place"
    in_city: bool = False
    bedrooms: str = "One bed"        # own place only
    room_type: str = "single"        # room only: single / double
    dwelling: str = "house"          # room only: house / apartment
    ensuite: bool = False            # room only
    include_gym: bool = False
    persona: str = "student"          # "student" or "professional" (working)
    needs_irp: bool = False          # non-EU/EEA/UK/Swiss: must register for an Irish Residence Permit


@dataclass
class Line:
    label: str
    amount: float
    source: str
    as_of: str
    confidence: str = "medium"


@dataclass
class Estimate:
    lines: list[Line] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    housing_label: str = ""
    essentials_detail: list = field(default_factory=list)   # (category, monthly, note)
    mesl_reference: float = 0.0      # official minimum budget, shown for comparison only
    irp: float = 0.0                 # one-off IRP registration fee (0 if not needed)

    @property
    def total(self) -> float:
        return round(sum(l.amount for l in self.lines), 2)

    @property
    def housing(self) -> float:
        return next((l.amount for l in self.lines if l.label.startswith("Housing")), 0.0)

    @property
    def deposit(self) -> float:
        """Deposit is capped at one month's rent (RTB, standard private rentals)."""
        return self.housing

    @property
    def move_in(self) -> float:
        """One-off cash needed to move in: deposit plus first month's rent in advance."""
        return round(self.deposit + self.housing, 2)

    @property
    def arrival_total(self) -> float:
        """All one-off cash on arrival: deposit + first month + IRP registration."""
        return round(self.move_in + self.irp, 2)

    @property
    def essentials(self) -> float:
        return next((l.amount for l in self.lines if l.label.startswith("Everyday essentials")), 0.0)


def estimate(c: Choices) -> Estimate:
    est = Estimate()

    if c.housing == "room":
        r = room_rent(c.county, c.room_type, c.dwelling, c.ensuite, c.in_city)
        if r is None:
            est.notes.append("No room-rent figure is published for this area, so housing is missing from the total.")
        else:
            est.housing_label = f"{c.room_type} room in a {c.dwelling} ({r['market']})"
            est.lines.append(Line(f"Housing: {est.housing_label}", r["rent"], r["source"], r["period"]))
            if r["note"]:
                est.notes.append(r["note"])
    else:
        r = own_place_rent(c.county, c.bedrooms, c.in_city)
        if r is None:
            est.notes.append("No rent figure is published for this home size here, so housing is missing from the total.")
        else:
            est.housing_label = f"{c.bedrooms.lower()} home ({r['area']})"
            est.lines.append(Line(f"Housing: {est.housing_label}", r["rent"], r["source"], r["period"]))
            if r["note"]:
                est.notes.append(r["note"])

    basket = essentials_basket(c.persona, c.housing == "own_place")
    est.essentials_detail = basket
    if c.housing == "own_place":
        est.notes.append("Gas and heating for a whole home are not included yet.")
    est.mesl_reference = catalogue_item("mesl_single_urban")["monthly_eur_low"]
    label = "student" if c.persona == "student" else "working professional"
    est.lines.append(Line(
        f"Everyday essentials ({label} budget)",
        round(sum(v for _, v, _ in basket), 2),
        "Estimated typical costs; official MESL share fills the one gap", "2026", "low"))

    if c.needs_irp:
        irp = catalogue_item("arrival_registration")
        est.irp = float(irp["monthly_eur_low"])
        est.notes.append("The IRP registration fee is a one-off, per adult, and is not part of the monthly total. "
                         "EU, EEA, UK and Swiss citizens do not pay it.")

    if c.include_gym:
        g = catalogue_item("gym_optional")
        if g and g["monthly_eur_low"] is not None:
            mid = round((g["monthly_eur_low"] + g["monthly_eur_high"]) / 2, 2)
            est.lines.append(Line("Optional: gym membership", mid, "Rough estimate", g["as_of"], "low"))
            est.notes.append("The gym figure is a rough estimate with no source yet.")
    return est
