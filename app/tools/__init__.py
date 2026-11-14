"""Tools layer: functions the LLM agents are allowed to call.

Each agent only gets its own tool list (scoping keeps agents focused).
TOOL_REGISTRY maps tool name → tool, so the workflow can execute any call.
"""

from app.tools.claims_tools import CLAIMS_TOOLS, STATE_IMAGE_PLACEHOLDER
from app.tools.policy_tools import POLICY_TOOLS
from app.tools.quote_tools import QUOTE_TOOLS

ALL_TOOLS = QUOTE_TOOLS + CLAIMS_TOOLS + POLICY_TOOLS
TOOL_REGISTRY = {t.name: t for t in ALL_TOOLS}

__all__ = ["QUOTE_TOOLS", "CLAIMS_TOOLS", "POLICY_TOOLS", "TOOL_REGISTRY", "STATE_IMAGE_PLACEHOLDER"]
