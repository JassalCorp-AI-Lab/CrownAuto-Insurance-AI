"""Premium calculation.

Illustrative model only: Canada has no single national rate table. The
structure (mandatory vs optional coverage, ACV, claims-free discount) is
realistic; the dollar figures are simplified.

Formula:
    ACV               = msrp x (1 - depreciation)
    Mandatory         = base premium by vehicle class
    Physical damage   = ACV x 2.5%        (Collision & Comprehensive plans)
    Claims-free disc. = (Mandatory + Physical damage) x discount %
    Waiver of Dep.    = flat $90 / year   (if chosen and car <= 2 years old)
    Total             = Mandatory + Physical damage - discount + Waiver (+ tax, 0%)
"""

# (max_age_in_years, depreciation_pct). Cars older than 5 years → 60%.
DEPRECIATION_SCHEDULE = [
    (0.5, 0.10),
    (1.0, 0.20),
    (2.0, 0.30),
    (3.0, 0.40),
    (4.0, 0.47),
    (5.0, 0.53),
]
DEFAULT_DEPRECIATION = 0.60


def calculate_acv(msrp: int, vehicle_age_years: float) -> int:
    """ACV = msrp × (1 − depreciation), rounded down to the dollar (CAD)."""
    depreciation_pct = DEFAULT_DEPRECIATION
    for max_age, dep_pct in DEPRECIATION_SCHEDULE:
        if vehicle_age_years <= max_age:
            depreciation_pct = dep_pct
            break
    return int(msrp * (1 - depreciation_pct))


# ─── Mandatory coverage premium ───────────────────────────────────

MANDATORY_BASE_PREMIUM = {
    "car": 1050,     # Sedans and hatchbacks
    "suv": 1150,     # SUVs and crossovers
    "pickup": 1300,  # Full-size pickups
}


def get_mandatory_premium(vehicle_class: str) -> int:
    """Illustrative mandatory-coverage premium; unknown classes priced as a car."""
    return MANDATORY_BASE_PREMIUM.get(vehicle_class.lower(), MANDATORY_BASE_PREMIUM["car"])


# ─── Claims-free discount + full premium calculation ───────────────

CLAIMS_FREE_DISCOUNT = {0: 0.0, 1: 0.05, 2: 0.10, 3: 0.15, 4: 0.20, 5: 0.25}

PHYSICAL_DAMAGE_RATE = 0.025       # Collision & Comprehensive = 2.5% of ACV / year
WAIVER_OF_DEPRECIATION_FEE = 90    # Flat endorsement fee, CAD / year
WAIVER_MAX_VEHICLE_AGE = 2.0       # Only offered on cars up to 2 years old
PROVINCIAL_PREMIUM_TAX_RATE = 0.0  # No GST/HST on auto insurance premiums

PLAN_KEYS = ("mandatory_only", "full_coverage", "waiver_of_depreciation")


def calculate_premium(
    msrp: int,
    vehicle_age_years: float,
    vehicle_class: str,
    claims_free_years: int = 0,
    plan: str = "full_coverage",
) -> dict:
    """Full premium breakdown for ONE plan."""
    acv = calculate_acv(msrp, vehicle_age_years)
    mandatory = get_mandatory_premium(vehicle_class)
    discount_pct = CLAIMS_FREE_DISCOUNT.get(min(max(claims_free_years, 0), 5), 0.0)

    if plan == "mandatory_only":
        discount = int(mandatory * discount_pct)
        subtotal = mandatory - discount
        tax = int(subtotal * PROVINCIAL_PREMIUM_TAX_RATE)
        return {
            "plan": "Mandatory Coverage Only",
            "acv": 0,  # Your own car isn't covered
            "mandatory_premium": mandatory,
            "physical_damage_premium": 0,
            "claims_free_discount": discount,
            "waiver_of_depreciation": 0,
            "eligible": True,
            "subtotal": subtotal,
            "premium_tax": tax,
            "total": subtotal + tax,
        }

    physical_damage = int(acv * PHYSICAL_DAMAGE_RATE)
    discount = int((mandatory + physical_damage) * discount_pct)

    waiver = 0
    eligible = True
    if plan == "waiver_of_depreciation":
        if vehicle_age_years <= WAIVER_MAX_VEHICLE_AGE:
            waiver = WAIVER_OF_DEPRECIATION_FEE
        else:
            eligible = False

    subtotal = mandatory + physical_damage - discount + waiver
    tax = int(subtotal * PROVINCIAL_PREMIUM_TAX_RATE)

    plan_name_map = {
        "full_coverage": "+ Collision & Comprehensive",
        "waiver_of_depreciation": "+ Collision & Comprehensive + Waiver of Depreciation",
    }

    result = {
        "plan": plan_name_map.get(plan, plan),
        "acv": acv,
        "mandatory_premium": mandatory,
        "physical_damage_premium": physical_damage,
        "claims_free_discount": discount,
        "waiver_of_depreciation": waiver,
        "eligible": eligible,
        "subtotal": subtotal,
        "premium_tax": tax,
        "total": subtotal + tax,
    }
    if not eligible:
        result["note"] = (
            f"Waiver of Depreciation is only offered on vehicles up to "
            f"{WAIVER_MAX_VEHICLE_AGE:g} years old"
        )
    return result


def get_three_quotes(
    msrp: int,
    vehicle_age_years: float,
    vehicle_class: str,
    claims_free_years: int = 0,
) -> list[dict]:
    """All THREE plan options, for side-by-side comparison."""
    return [
        calculate_premium(msrp, vehicle_age_years, vehicle_class, claims_free_years, p)
        for p in PLAN_KEYS
    ]
