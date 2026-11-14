"""Tools for the Claims agent, including vision damage analysis."""

import json

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from app.domain import claims
from app.llm import get_chat_model, parse_json_response

# The Claims agent passes this placeholder instead of raw image bytes. The
# workflow's tool executor replaces it with the real photo from graph state,
# so the LLM never has to handle (or invent) base64 data.
STATE_IMAGE_PLACEHOLDER = "__USE_STATE_IMAGE__"


class PolicyVerifyInput(BaseModel):
    policy_number: str = Field(description="Policy number, e.g. POL-2026-12345")


@tool("verify_policy", args_schema=PolicyVerifyInput)
def verify_policy(policy_number: str) -> dict:
    """Verify a policy is active and within coverage period.

    For demo purposes, accepts any policy number matching POL-YYYY-NNNNN format.
    In production this would query the policy database.
    """
    return claims.verify_policy(policy_number)


class DamageAnalysisInput(BaseModel):
    image_b64: str = Field(
        description=f"Base64-encoded damage photo. Pass '{STATE_IMAGE_PLACEHOLDER}' "
        "to use the photo the customer uploaded."
    )
    incident_description: str = Field(default="", description="Optional description of how the incident occurred")


VISION_PROMPT = """You are an auto insurance damage appraiser in Canada. Analyze this car damage photo
and respond ONLY with valid JSON (no markdown fences, no extra text).

Incident description from customer: {incident_description}

Required JSON schema:
{{
  "affected_parts": [
    {{"part": "front bumper", "severity": "minor|moderate|severe"}},
    ...
  ],
  "overall_severity": "minor|moderate|severe|total_loss",
  "estimated_cost_cad": <integer estimate of repair cost in Canadian dollars>,
  "description": "<one-sentence damage summary>",
  "repair_recommendation": "<repair|replace|total_loss>"
}}

Cost guidance:
- Minor scratch/dent: $500–2,000
- Moderate panel damage: $2,000–7,500
- Severe damage (panel + light + bumper): $7,500–25,000
- Total loss: > 75% of vehicle ACV

If the photo does not show a vehicle, return {{"error": "no_vehicle_detected", "description": "<what the photo shows>"}}.
"""


@tool("analyze_damage_image", args_schema=DamageAnalysisInput)
def analyze_damage_image(image_b64: str, incident_description: str = "") -> dict:
    """Analyze a damage photo with the vision model and classify severity.

    Returns affected parts, severity per part, and overall severity rating.
    """
    if not image_b64 or len(image_b64) < 100:
        return {"error": "No valid image provided"}

    # Accept a full data URL (keeps the real mime type) or raw base64.
    data_url = image_b64 if image_b64.startswith("data:") else f"data:image/jpeg;base64,{image_b64}"
    prompt = VISION_PROMPT.format(incident_description=incident_description or "(none provided)")

    content = ""
    try:
        response = get_chat_model("vision").invoke([{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": data_url}},
            ],
        }])
        content = response.text  # plain text even if the model returns content blocks
        return parse_json_response(content)
    except json.JSONDecodeError as e:
        return {"error": f"Vision response parse error: {e}", "raw_response": str(content)[:500]}
    except Exception as e:
        return {"error": f"Vision analysis failed: {type(e).__name__}: {e}"}


class PayoutInput(BaseModel):
    estimated_repair_cost_cad: int = Field(description="Repair cost estimate from damage analysis, in CAD")
    policy_acv: int = Field(description="Vehicle ACV (Actual Cash Value) from the policy")
    plan: str = Field(default="Collision & Comprehensive", description="Policy plan name")
    deductible_cad: int = Field(default=500, description="Collision/comprehensive deductible (default $500)")
    purchase_price_cad: int = Field(
        default=0, description="Original purchase price — only used with Waiver of Depreciation on a total loss"
    )


@tool("estimate_payout", args_schema=PayoutInput)
def estimate_payout(
    estimated_repair_cost_cad: int,
    policy_acv: int,
    plan: str = "Collision & Comprehensive",
    deductible_cad: int = 500,
    purchase_price_cad: int = 0,
) -> dict:
    """Calculate the estimated insurance payout for a claim.

    Considers the ACV cap, total-loss rule, Waiver of Depreciation and
    the deductible.
    """
    return claims.estimate_payout(estimated_repair_cost_cad, policy_acv, plan, deductible_cad, purchase_price_cad)


CLAIMS_TOOLS = [verify_policy, analyze_damage_image, estimate_payout]
