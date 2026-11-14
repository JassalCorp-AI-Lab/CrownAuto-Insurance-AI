from app.domain import claims


def test_verify_policy_format():
    assert claims.verify_policy(" pol-2026-12345 ")["valid"] is True
    assert claims.verify_policy("12345")["valid"] is False


def test_repair_payout_is_cost_minus_deductible():
    p = claims.estimate_payout(6_800, 28_000)
    assert p["estimated_payout_cad"] == 6_300
    assert p["out_of_pocket_cad"] == 500
    assert p["is_total_loss"] is False
    assert p["appraiser_inspection_required"] is True  # over $5,000


def test_repair_below_deductible_pays_nothing():
    p = claims.estimate_payout(300, 28_000)
    assert p["estimated_payout_cad"] == 0
    assert p["out_of_pocket_cad"] == 300
    assert p["appraiser_inspection_required"] is False


def test_total_loss_paid_at_acv():
    # Written-off 2-year-old Civic with ACV $21,000 → $20,500
    p = claims.estimate_payout(20_000, 21_000)
    assert p["is_total_loss"] is True
    assert p["estimated_payout_cad"] == 20_500


def test_total_loss_with_waiver_pays_purchase_price():
    p = claims.estimate_payout(20_000, 21_000, plan="Waiver of Depreciation", purchase_price_cad=30_000)
    assert p["estimated_payout_cad"] == 29_500
