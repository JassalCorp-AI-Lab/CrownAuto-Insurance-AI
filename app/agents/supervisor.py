"""The supervisor: decides which specialist handles each message.

Routing rules:
- A photo uploaded on this turn always goes to Claims (no LLM call needed).
  The photo stays in state for later turns, but does not force the route.
- Otherwise an LLM classifies the message. It is told which agent handled
  the previous turn and what it said, so short follow-ups
  ("POL-2026-12345", "which plan is best?") stay with the same specialist.
"""

import json

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.agents.prompts import SUPERVISOR_PROMPT
from app.agents.state import INTENT_TO_AGENT, AgentState
from app.llm import get_chat_model, parse_json_response

DEFAULT_INTENT = "policy_qa"


def supervisor_node(state: AgentState) -> dict:
    """Classify the latest user message and choose the next agent."""
    messages = state.get("messages", [])
    user_messages = [m for m in messages if isinstance(m, HumanMessage)]
    if not user_messages:
        return _route(DEFAULT_INTENT)

    # Deterministic shortcut — no LLM call needed.
    if state.get("new_image"):
        return _route("claim")

    prompt = _build_router_input(state, user_messages)
    response = get_chat_model("router").invoke([
        SystemMessage(content=SUPERVISOR_PROMPT),
        HumanMessage(content=prompt),
    ])

    try:
        intent = parse_json_response(response.text).get("intent", DEFAULT_INTENT)
    except (json.JSONDecodeError, AttributeError):
        intent = DEFAULT_INTENT
    return _route(intent)


def route_from_supervisor(state: AgentState) -> str:
    """Conditional edge: which node runs after the supervisor."""
    return state.get("next_agent") or INTENT_TO_AGENT[DEFAULT_INTENT]


# ─── helpers ──────────────────────────────────────────────────────────
def _route(intent: str) -> dict:
    if intent not in INTENT_TO_AGENT:
        intent = DEFAULT_INTENT
    return {"intent": intent, "next_agent": INTENT_TO_AGENT[intent]}


def _build_router_input(state: AgentState, user_messages: list) -> str:
    latest = user_messages[-1].text
    previous_intent = state.get("intent")
    if not previous_intent or len(user_messages) < 2:
        return f"User's new message:\n{latest}"

    last_reply = _last_ai_reply(state["messages"][:-1])[:600]
    return (
        f"Previous turn was handled by the '{previous_intent}' agent.\n"
        f'Its last reply was:\n"""{last_reply}"""\n\n'
        f"User's new message:\n{latest}"
    )


def _last_ai_reply(messages: list) -> str:
    for m in reversed(messages):
        if isinstance(m, AIMessage) and m.text and not m.tool_calls:
            return m.text
    return ""
