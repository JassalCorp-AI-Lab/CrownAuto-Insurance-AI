"""Premium maths — hand-checked reference quotes."""

import pytest

from app.domain import pricing


@pytest.mark.parametrize(
    "age, expected",
    [(0.25, 27_000), (1.0, 24_000), (2.0, 21_000), (3.0, 18_000), (5.0, 14_100), (8.0, 12_000)],
)
def test_acv_for_30k_car(age, expected):
    assert pricing.calculate_acv(30_000, age) == expected


def test_mandatory_premium_by_class():
    assert pricing.get_mandatory_premium("car") == 1050
    assert pricing.get_mandatory_premium("SUV") == 1150
    assert pricing.get_mandatory_premium("pickup") == 1300
    assert pricing.get_mandatory_premium("van") == 1050  # unknown → priced as car


def test_three_quotes_for_reference_civic():
    # 2-year-old Civic, 1 claims-free year → $998 / $1,497 / $1,587
    quotes = pricing.get_three_quotes(30_000, 2.0, "car", 1)
    assert [q["total"] for q in quotes] == [998, 1497, 1587]

    full = quotes[1]
    assert full["acv"] == 21_000
    assert full["physical_damage_premium"] == 525
    assert full["claims_free_discount"] == 78


def test_waiver_not_offered_on_cars_over_two_years():
    q = pricing.calculate_premium(40_000, 3.0, "suv", 0, "waiver_of_depreciation")
    assert q["eligible"] is False
    assert q["waiver_of_depreciation"] == 0
    assert "only offered" in q["note"]


def test_claims_free_discount_caps_at_25_percent():
    q = pricing.calculate_premium(30_000, 2.0, "car", 12, "mandatory_only")
    assert q["claims_free_discount"] == int(1050 * 0.25)


def test_negative_claims_free_years_treated_as_zero():
    q = pricing.calculate_premium(30_000, 2.0, "car", -3, "mandatory_only")
    assert q["claims_free_discount"] == 0
