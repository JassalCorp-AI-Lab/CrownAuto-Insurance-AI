"""Tools for the Quote agent.

A tool = Pydantic input schema + a function decorated with @tool. The LLM
reads the schema's field descriptions and the docstring to decide when and
how to call it, so keep them clear. The function body just delegates to the
domain layer.
"""

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from app.domain import pricing, territory, vehicles


class VehicleLookupInput(BaseModel):
    # Pydantic reserves the "model_" prefix; allow our car-model field name.
    model_config = {"protected_namespaces": ()}
    model_query: str = Field(description="Vehicle model name to look up (e.g., 'Civic', 'RAV4', 'F-150')")


@tool("vehicle_lookup", args_schema=VehicleLookupInput)
def vehicle_lookup(model_query: str) -> dict:
    """Look up vehicle specs (make, model, vehicle class, MSRP).

    Use this when the user mentions a car model. Returns vehicle metadata
    needed to calculate the premium.
    """
    vehicle = vehicles.lookup_vehicle(model_query)
    if vehicle is None:
        return {
            "found": False,
            "supported_models": vehicles.supported_models(),
            "message": f"Model '{model_query}' not found. Try one of the supported models.",
        }
    return {"found": True, **vehicle}


class PremiumInput(BaseModel):
    msrp: int = Field(description="Vehicle MSRP (original price) in CAD")
    vehicle_age_years: float = Field(description="Vehicle age in years (e.g. 2.5)")
    vehicle_class: str = Field(description="Vehicle class: 'car', 'suv' or 'pickup'")
    claims_free_years: int = Field(default=0, description="Years without an at-fault claim (0–5+)")


@tool("calculate_premium", args_schema=PremiumInput)
def calculate_premium(msrp: int, vehicle_age_years: float, vehicle_class: str, claims_free_years: int = 0) -> dict:
    """Calculate auto insurance premium quotes for all 3 plans.

    Returns Mandatory Coverage Only, + Collision & Comprehensive, and
    + Waiver of Depreciation quotes with a full breakdown (ACV, mandatory,
    physical damage, claims-free discount, premium tax, total).
    """
    quotes = pricing.get_three_quotes(msrp, vehicle_age_years, vehicle_class, claims_free_years)
    return {"quotes": quotes, "currency": "CAD"}


class PostalCodeInput(BaseModel):
    postal_code: str = Field(description="Canadian postal code, e.g. 'M5V 3L9' (the first 3 characters are enough)")


@tool("postal_code_risk", args_schema=PostalCodeInput)
def postal_code_risk(postal_code: str) -> dict:
    """Check the collision/theft risk tier for a Canadian postal code.

    Returns risk tier (low/medium/high) and any premium loading.
    Used during underwriting to adjust quotes for higher-risk territories.
    """
    return territory.postal_code_risk(postal_code)


QUOTE_TOOLS = [vehicle_lookup, calculate_premium, postal_code_risk]
