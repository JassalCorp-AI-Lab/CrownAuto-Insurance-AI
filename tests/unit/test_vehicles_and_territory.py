import pytest

from app.domain import territory, vehicles


@pytest.mark.parametrize(
    "query, model",
    [("civic", "Civic"), ("RAV4", "RAV4"), ("Honda CR-V", "CR-V"), ("ford f-150", "F-150"), ("Model Y", "Model Y")],
)
def test_lookup_vehicle_is_fuzzy(query, model):
    assert vehicles.lookup_vehicle(query)["model"] == model


@pytest.mark.parametrize("query", ["BMW", "", "   "])
def test_lookup_vehicle_not_found(query):
    assert vehicles.lookup_vehicle(query) is None


@pytest.mark.parametrize(
    "postal, tier, loading",
    [("L6P 1A1", "high", 15), ("m5v3l9", "medium", 5), ("V6B 1A1", "medium", 5), ("K1A 0B1", "low", 0)],
)
def test_postal_code_risk(postal, tier, loading):
    result = territory.postal_code_risk(postal)
    assert (result["risk_tier"], result["loading_pct"]) == (tier, loading)
