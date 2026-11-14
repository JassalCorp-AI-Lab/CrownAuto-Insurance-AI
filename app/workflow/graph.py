"""Builds the LangGraph workflow.

    START → supervisor ─┬─▶ quote ─────┐
                        ├─▶ claims ────┼─▶ tools ─▶ back to the same agent
                        └─▶ policy_qa ─┘
                          (no tool calls) ─▶ END
"""

from langchain_core.messages import AIMessage
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from app.agents.specialists import (
    claims_agent_node,
    policy_qa_agent_node,
    quote_agent_node,
)
from app.agents.state import INTENT_TO_AGENT, AgentState
from app.agents.supervisor import route_from_supervisor, supervisor_node
from app.workflow.tool_executor import tool_executor_node

AGENT_NODES = {
    "quote": quote_agent_node,
    "claims": claims_agent_node,
    "policy_qa": policy_qa_agent_node,
}


def should_use_tools(state: AgentState) -> str:
    """After an agent runs: did it ask for tools, or is the reply final?"""
    last_msg = state["messages"][-1]
    return "tools" if isinstance(last_msg, AIMessage) and last_msg.tool_calls else "end"


def route_after_tools(state: AgentState) -> str:
    """After tools run: go back to the agent that requested them."""
    return INTENT_TO_AGENT.get(state.get("intent") or "policy_qa", "policy_qa")


def build_graph(checkpointer: BaseCheckpointSaver | None = None):
    """Compile the workflow.

    The checkpointer stores conversation state per thread_id. MemorySaver keeps
    it in RAM (lost on restart); pass a SQLite/Postgres saver to persist it.
    """
    graph = StateGraph(AgentState)
    graph.add_node("supervisor", supervisor_node)
    graph.add_node("tools", tool_executor_node)
    for name, node in AGENT_NODES.items():
        graph.add_node(name, node)

    agent_names = {name: name for name in AGENT_NODES}
    graph.add_edge(START, "supervisor")
    graph.add_conditional_edges("supervisor", route_from_supervisor, agent_names)
    for name in AGENT_NODES:
        graph.add_conditional_edges(name, should_use_tools, {"tools": "tools", "end": END})
    graph.add_conditional_edges("tools", route_after_tools, agent_names)

    return graph.compile(checkpointer=checkpointer or MemorySaver())
