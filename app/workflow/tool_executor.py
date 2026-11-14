"""Graph node that runs the tools an agent asked for.

We use a custom node instead of LangGraph's prebuilt ToolNode because the
vision tool needs the photo from state, not from the LLM's arguments.
"""

import json

from langchain_core.messages import AIMessage, ToolMessage

from app.agents.state import AgentState
from app.tools import TOOL_REGISTRY


def tool_executor_node(state: AgentState) -> dict:
    """Execute every tool call in the latest AI message; return the results."""
    last_msg = state["messages"][-1]
    if not isinstance(last_msg, AIMessage) or not last_msg.tool_calls:
        return {}
    return {"messages": [_execute(tool_call, state) for tool_call in last_msg.tool_calls]}


def _execute(tool_call: dict, state: AgentState) -> ToolMessage:
    name = tool_call["name"]
    args = dict(tool_call["args"])

    if name not in TOOL_REGISTRY:
        return _result(tool_call, {"error": f"Unknown tool: {name}"})

    # Swap the image placeholder for the real photo kept in state.
    if name == "analyze_damage_image":
        if not state.get("damage_image_b64"):
            return _result(tool_call, {"error": "No damage image in state"})
        args["image_b64"] = state["damage_image_b64"]

    try:
        output = TOOL_REGISTRY[name].invoke(args)
    except Exception as e:  # Tell the agent what went wrong instead of crashing
        output = {"error": f"{type(e).__name__}: {e}"}
    return _result(tool_call, output)


def _result(tool_call: dict, content: dict) -> ToolMessage:
    # tool_call_id links this result back to the call the agent made.
    return ToolMessage(
        content=json.dumps(content, default=str),
        tool_call_id=tool_call["id"],
        name=tool_call["name"],
    )
