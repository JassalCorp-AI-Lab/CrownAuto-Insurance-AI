"""Policy verification and claim payout rules."""

def verify_policy(policy_number: str) -> dict:
    """Mock policy DB: any POL-YYYY-NNNNN number is an active policy."""
    pn = policy_number.strip().upper()
    if not pn.startswith("POL-") or len(pn) < 12:
        return {
            "valid": False,
            "policy_number": pn,
            "reason": "Invalid policy number format. Expected: POL-YYYY-NNNNN",
        }
    return {
        "valid": True,
        "policy_number": pn,
        "status": "ACTIVE",
        "plan": "Collision & Comprehensive",
        "acv": 28_000,
        "deductible": 500,
        "expires_on": "2027-03-31",
        "vehicle": "Honda Civic EX",
        "policyholder": "Test Customer",
    }


TOTAL_LOSS_THRESHOLD = 0.75     # Repair > 75% of ACV → written off
APPRAISER_THRESHOLD_CAD = 5_000  # Mock CrownAuto rule


def estimate_payout(
    estimated_repair_cost_cad: int,
    policy_acv: int,
    plan: str = "Collision & Comprehensive",
    deductible_cad: int = 500,
    purchase_price_cad: int = 0,
) -> dict:
    """Estimated payout considering ACV cap, total-loss rule, waiver and deductible."""
    is_total_loss = estimated_repair_cost_cad > (policy_acv * TOTAL_LOSS_THRESHOLD)

    if is_total_loss:
        if "waiver" in plan.lower() and purchase_price_cad > 0:
            settlement_basis = purchase_price_cad
            plan_note = "Total loss — Waiver of Depreciation pays the original purchase price"
        else:
            settlement_basis = policy_acv
            plan_note = "Total loss — paid at Actual Cash Value (ACV)"
        payout = max(0, settlement_basis - deductible_cad)
        out_of_pocket = deductible_cad
    else:
        payout = max(0, min(estimated_repair_cost_cad - deductible_cad, policy_acv))
        plan_note = "Repair — insurer pays the repair cost minus your deductible"
        out_of_pocket = estimated_repair_cost_cad - payout

    return {
        "estimated_repair_cost_cad": estimated_repair_cost_cad,
        "deductible_cad": deductible_cad,
        "estimated_payout_cad": payout,
        "out_of_pocket_cad": out_of_pocket,
        "is_total_loss": is_total_loss,
        "plan_note": plan_note,
        "appraiser_inspection_required": estimated_repair_cost_cad > APPRAISER_THRESHOLD_CAD,
        "police_report_note": (
            "Most provinces require reporting a collision to police if anyone is "
            "injured or damage exceeds a set threshold (commonly $1,000–$2,000)."
        ),
    }
