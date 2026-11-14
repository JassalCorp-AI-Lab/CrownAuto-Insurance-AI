"""Territory (postal code) risk rating."""

# Parts of Brampton and Vaughan, Ontario
HIGH_RISK_FSAS = {"L6P", "L6R", "L6S", "L6T", "L6V", "L6W", "L6X", "L6Y", "L6Z", "L4H", "L4L"}
# Toronto (M), Montréal (H), Vancouver (V5, V6), Calgary (T2, T3), Mississauga (L5)
MEDIUM_RISK_PREFIXES = ("M", "H", "V5", "V6", "T2", "T3", "L5")


def postal_code_risk(postal_code: str) -> dict:
    """Risk tier (low/medium/high) and premium loading for a Canadian postal code."""
    fsa = postal_code.upper().replace(" ", "")[:3]
    if fsa in HIGH_RISK_FSAS:
        tier, loading, note = "high", 15, "Territory with high collision and theft claim costs"
    elif fsa.startswith(MEDIUM_RISK_PREFIXES):
        tier, loading, note = "medium", 5, "Dense urban territory"
    else:
        tier, loading, note = "low", 0, "Standard risk"
    return {
        "postal_code": postal_code,
        "fsa": fsa,
        "risk_tier": tier,
        "loading_pct": loading,
        "note": note,
    }
