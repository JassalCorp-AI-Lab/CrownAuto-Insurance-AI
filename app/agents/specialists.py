"""The three specialist agents.

Each specialist is just: a system prompt + a list of tools it may call. They
all share `_run_agent`; only the prompt and tools differ.
"""

from langchain_core.messages import AIMessage, BaseMessage, SystemMessage, ToolMessage

from app.agents import prompts
from app.agents.state import AgentState
from app.llm import get_chat_model
from app.tools import CLAIMS_TOOLS, POLICY_TOOLS, QUOTE_TOOLS, STATE_IMAGE_PLACEHOLDER


def quote_agent_node(state: AgentState) -> dict:
    return _run_agent(state, prompts.QUOTE_AGENT_PROMPT, QUOTE_TOOLS)


def claims_agent_node(state: AgentState) -> dict:
    # The agent never sees the image bytes; we just tell it whether one exists.
    if state.get("damage_image_b64"):
        fresh = " The customer attached it with their latest message." if state.get("new_image") else ""
        note = prompts.CLAIMS_IMAGE_AVAILABLE_NOTE.format(fresh=fresh, placeholder=STATE_IMAGE_PLACEHOLDER)
    else:
        note = prompts.CLAIMS_NO_IMAGE_NOTE
    return _run_agent(state, prompts.CLAIMS_AGENT_PROMPT + note, CLAIMS_TOOLS)


def policy_qa_agent_node(state: AgentState) -> dict:
    return _run_agent(state, prompts.POLICY_QA_PROMPT, POLICY_TOOLS)


# ─── shared logic ─────────────────────────────────────────────────────
def _run_agent(state: AgentState, system_prompt: str, tools: list) -> dict:
    """Call the LLM with the agent's prompt + conversation; it may request tools."""
    llm = get_chat_model("agent").bind_tools(tools)
    history = sanitize_history(state.get("messages", []))
    response = llm.invoke([SystemMessage(content=system_prompt)] + history)
    return {"messages": [response]}


def sanitize_history(messages: list[BaseMessage]) -> list[BaseMessage]:
    """Remove tool calls that never got a result (e.g. after a crash).

    OpenAI rejects a history where an assistant tool call has no matching
    tool result, which would break every later turn of the conversation.
    """
    answered_ids = {m.tool_call_id for m in messages if isinstance(m, ToolMessage)}
    kept_call_ids: set[str] = set()
    cleaned: list[BaseMessage] = []

    for m in messages:
        if isinstance(m, AIMessage) and m.tool_calls:
            call_ids = {tc["id"] for tc in m.tool_calls}
            if not call_ids <= answered_ids:
                continue  # dangling tool call → drop
            kept_call_ids |= call_ids
        if isinstance(m, ToolMessage) and m.tool_call_id not in kept_call_ids:
            continue  # orphaned tool result → drop
        cleaned.append(m)
    return cleaned
