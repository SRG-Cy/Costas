"""Tests for costs.py. Expected values were checked by hand against the source PDF/CSV."""
import pytest

import costs
from costs import Choices

MESL = 1243.67


def test_county_list_is_complete():
    assert len(costs.counties()) == 26


def test_latest_period():
    assert costs.latest_period() == "2025H2"


def test_galway_city_double_room_no_ensuite_matches_daft_page_32():
    r = costs.room_rent("Galway", "double", "house", ensuite=False, in_city=True)
    assert r["rent"] == 700 and r["market"] == "Galway City" and r["period"] == "2026Q1"


def test_mayo_single_room_uses_connacht_ulster_region_page_15():
    r = costs.room_rent("Mayo", "single", "house", ensuite=False)
    assert r["rent"] == 527 and r["market"] == "Connacht-Ulster (ex-Galway)"


def test_dublin_single_room_in_apartment_with_ensuite():
    assert costs.room_rent("Dublin", "single", "apartment", ensuite=True)["rent"] == 1082


def test_unpublished_room_type_falls_back_and_says_so():
    # Single room in a house WITH ensuite is blank for Connacht-Ulster in the report.
    r = costs.room_rent("Mayo", "single", "house", ensuite=True)
    assert r["rent"] == 527 and r["note"]


def test_own_place_galway_county_two_bed():
    r = costs.own_place_rent("Galway", "Two bed")
    assert r["rent"] == pytest.approx(1488.92) and r["period"] == "2025H2"


def test_own_place_city_option_is_higher_than_county_in_galway():
    city = costs.own_place_rent("Galway", "One bed", in_city=True)
    county = costs.own_place_rent("Galway", "One bed")
    assert city["area"] == "Galway City" and city["rent"] == pytest.approx(1211.2)
    assert county["rent"] == pytest.approx(1101.09)


def test_city_option_ignored_for_county_without_city():
    assert costs.city_option("Mayo") is None
    assert costs.own_place_rent("Mayo", "One bed", in_city=True)["area"] == "Mayo"


def test_estimate_total_is_housing_plus_essentials():
    e = costs.estimate(Choices(county="Galway", housing="room", in_city=True, room_type="double", dwelling="house"))
    assert e.housing == 700 and e.essentials == pytest.approx(MESL) and e.total == pytest.approx(700 + MESL)


def test_gym_is_added_only_when_selected_and_flagged_low_confidence():
    base = costs.estimate(Choices(county="Dublin", housing="room")).total
    with_gym = costs.estimate(Choices(county="Dublin", housing="room", include_gym=True))
    assert with_gym.total == pytest.approx(base + 45)
    assert with_gym.lines[-1].confidence == "low"


def test_all_26_counties_produce_a_total_for_both_housing_types():
    for county in costs.counties():
        for housing in ("room", "own_place"):
            e = costs.estimate(Choices(county=county, housing=housing))
            assert e.housing > 0, (county, housing, e.notes)


def test_catalogue_has_no_text_in_number_columns_and_verified_rows_have_sources():
    for row in costs.catalogue():
        if row["status"] == "verified":
            assert row["source_url"] and row["as_of"], row["item_id"]
            if row["category"] != "one_off":  # one-off rules are computed from rent, not a fixed value
                assert row["monthly_eur_low"] is not None, row["item_id"]


def test_move_in_is_deposit_plus_first_month():
    est = costs.estimate(costs.Choices(county="Galway", housing="own", bedrooms="Two bed", in_city=False))
    assert est.deposit == est.housing
    assert est.move_in == round(2 * est.housing, 2)


def test_irp_is_one_off_and_not_in_monthly_total():
    base = costs.estimate(Choices(county="Galway", housing="room"))
    irp = costs.estimate(Choices(county="Galway", housing="room", needs_irp=True))
    assert base.irp == 0 and irp.irp == 300
    assert irp.total == base.total
    assert irp.arrival_total == round(base.arrival_total + 300, 2)


# ---------------------------------------------------------------- AI helpers (model is mocked)
import ai


def test_clean_answers_drops_invalid_values():
    out = ai.clean_answers({"county": "galway", "in_city": True, "housing": "castle", "bedrooms": "Nine bed",
                            "room_type": "double", "needs_irp": "yes", "evil": "x"})
    assert out == {"county": "Galway", "in_city": True, "room_type": "double"}


def test_in_city_ignored_when_county_has_no_city():
    assert ai.clean_answers({"county": "Mayo", "in_city": True})["in_city"] is False


def test_parse_situation_survives_bad_output(monkeypatch):
    monkeypatch.setattr(ai, "available", lambda: True)
    monkeypatch.setattr(ai, "_complete", lambda *a, **k: "sorry, I cannot")
    assert ai.parse_situation("student moving to Galway") == {}


def test_parse_situation_happy_path(monkeypatch):
    monkeypatch.setattr(ai, "available", lambda: True)
    monkeypatch.setattr(ai, "_complete", lambda *a, **k: '```json\n{"county": "Galway", "in_city": true, "housing": "room"}\n```')
    assert ai.parse_situation("room in Galway city") == {"county": "Galway", "in_city": True, "housing": "room"}


def test_explain_rejects_invented_numbers(monkeypatch):
    est = costs.estimate(Choices(county="Galway", housing="room", needs_irp=True))
    monkeypatch.setattr(ai, "available", lambda: True)
    monkeypatch.setattr(ai, "_complete", lambda *a, **k: "You will pay €9,999 a month.")
    assert ai.explain(est, "Galway") is None
    ok = f"Rent is €{round(est.housing):,} and the total is €{round(est.total):,} a month."
    monkeypatch.setattr(ai, "_complete", lambda *a, **k: ok)
    assert ai.explain(est, "Galway") == ok
