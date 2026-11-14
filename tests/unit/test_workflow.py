"""Graph plumbing: tool executor, routing, history cleanup, chunking, parsing."""

import json

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from app.agents.specialists import sanitize_history
from app.agents.supervisor import supervisor_node
from app.knowledge.vector_store import chunk_documents
from app.llm import parse_json_response
from app.workflow import build_graph
from app.workflow.graph import route_after_tools, should_use_tools
from app.workflow.tool_executor import tool_executor_node
from tests.conftest import tool_call


def test_graph_has_all_nodes():
    assert {"supervisor", "quote", "claims", "policy_qa", "tools"} <= set(build_graph().nodes)


def test_supervisor_routes_new_photo_to_claims_without_llm():
    state = {"messages": [HumanMessage("photo")], "damage_image_b64": "data:x", "new_image": True}
    assert supervisor_node(state) == {"intent": "claim", "next_agent": "claims"}


def test_tool_executor_runs_tool():
    out = tool_executor_node({"messages": [tool_call("vehicle_lookup", {"model_query": "civic"})]})
    assert json.loads(out["messages"][0].content)["msrp"] == 30_000


def test_tool_executor_reports_missing_image():
    msg = tool_call("analyze_damage_image", {"image_b64": "__USE_STATE_IMAGE__"})
    assert "No damage image" in tool_executor_node({"messages": [msg]})["messages"][0].content


def test_tool_executor_reports_unknown_tool():
    assert "Unknown tool" in tool_executor_node({"messages": [tool_call("nope", {})]})["messages"][0].content


def test_routing_helpers():
    assert should_use_tools({"messages": [tool_call("verify_policy", {})]}) == "tools"
    assert should_use_tools({"messages": [AIMessage(content="hi")]}) == "end"
    assert route_after_tools({"intent": "claim"}) == "claims"
    assert route_after_tools({}) == "policy_qa"


def test_sanitize_history_drops_unanswered_tool_calls():
    dangling = tool_call("vehicle_lookup", {"model_query": "civic"}, "a")
    msgs = [
        HumanMessage("hi"),
        dangling,  # never got a ToolMessage
        HumanMessage("again"),
        tool_call("vehicle_lookup", {"model_query": "civic"}, "b"),
        ToolMessage(content="{}", tool_call_id="b", name="vehicle_lookup"),
        AIMessage(content="done"),
    ]
    cleaned = sanitize_history(msgs)
    assert dangling not in cleaned and len(cleaned) == 5


def test_knowledge_base_chunking():
    chunks = chunk_documents()
    assert len(chunks) >= 15
    assert {c["source"] for c in chunks} == {"canada_auto_insurance_guidelines.md", "policy_terms.md", "faqs.md"}


@pytest.mark.parametrize("text", ['{"a": 1}', '```json\n{"a": 1}\n```', '```\n{"a": 1}\n```'])
def test_parse_json_response_strips_fences(text):
    assert parse_json_response(text) == {"a": 1}
