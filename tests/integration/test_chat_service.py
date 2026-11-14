"""Full multi-turn conversations through the real graph with a scripted LLM."""

from langchain_core.messages import AIMessage

from app.services.chat_service import ChatService
from app.workflow import build_graph
from tests.conftest import tool_call

PHOTO = "data:image/png;base64," + "A" * 200


def events_of(service, message, image=None, session="s1"):
    return list(service.stream(message, session, image))


def test_quote_then_claim_then_question(fake_llm):
    model = fake_llm(
        [
            # Turn 1 — router, then quote agent chains two tools
            AIMessage(content='{"intent": "quote"}'),
            tool_call("vehicle_lookup", {"model_query": "Civic"}, "1"),
            tool_call("calculate_premium", {"msrp": 30000, "vehicle_age_years": 2, "vehicle_class": "car", "claims_free_years": 1}, "2"),
            AIMessage(content="Plans: $998 / $1,497 / $1,587"),
            # Turn 2 — photo upload: no router call (shortcut)
            tool_call("analyze_damage_image", {"image_b64": "__USE_STATE_IMAGE__"}, "3"),
            tool_call("estimate_payout", {"estimated_repair_cost_cad": 6800, "policy_acv": 28000}, "4"),
            AIMessage(content="Estimated payout: $6,300"),
            # Turn 3 — photo still in state, but router must run again
            AIMessage(content='{"intent": "policy_qa"}'),
            AIMessage(content="A deductible is the amount you pay first."),
        ],
        vision=[AIMessage(content='```json\n{"estimated_cost_cad": 6800}\n```')],
    )
    service = ChatService(build_graph())

    turn1 = events_of(service, "Quote for my 2-year-old Civic, 1 claims-free year")
    assert [e["type"] for e in turn1] == ["route", "tool_call", "tool_result", "tool_call", "tool_result", "final"]
    assert turn1[-1]["tools_used"] == ["vehicle_lookup", "calculate_premium"]
    assert "$1,497" in turn1[-1]["reply"]

    turn2 = events_of(service, "Here's the damage", PHOTO)
    assert turn2[0]["agent"] == "claims"
    assert turn2[1]["args"]["image_b64"] == "<uploaded photo>"  # bytes never sent to UI
    assert all(e["ok"] for e in turn2 if e["type"] == "tool_result")

    turn3 = events_of(service, "What is a deductible?")
    assert turn3[0]["agent"] == "policy_qa"  # not stuck on claims
    assert turn3[-1]["tools_used"] == []

    assert model.replies == []  # every scripted step was used


def blocks(text: str) -> list[dict]:
    """Content in the 'list of blocks' format newer OpenAI models return."""
    return [
        {"type": "reasoning", "summary": []},
        {"type": "text", "text": text, "annotations": [], "id": "msg_123", "phase": "final_answer"},
    ]


def test_content_block_replies_are_read_as_plain_text(fake_llm):
    fake_llm(
        [
            AIMessage(content=blocks('{"intent": "claim"}')),  # router
            tool_call("analyze_damage_image", {"image_b64": "__USE_STATE_IMAGE__"}, "v1"),
            AIMessage(content=blocks("**Estimated payout:** $6,300")),  # final reply
        ],
        vision=[AIMessage(content=blocks('{"estimated_cost_cad": 6800}'))],
    )
    service = ChatService(build_graph())
    # Seed a photo on an earlier turn so this turn must go through the router.
    service._graph.update_state({"configurable": {"thread_id": "blocks"}}, {"damage_image_b64": PHOTO})

    events = events_of(service, "My bumper is damaged", session="blocks")
    assert events[0]["agent"] == "claims"                     # router JSON parsed
    assert events[2] == {"type": "tool_result", "name": "analyze_damage_image", "ok": True}  # vision JSON parsed
    assert events[-1]["reply"] == "**Estimated payout:** $6,300"  # no raw block list


def test_missing_api_key_becomes_error_event(monkeypatch):
    from app.llm import MissingAPIKeyError

    def no_key(_role):
        raise MissingAPIKeyError("OPENAI_API_KEY is not set.")

    monkeypatch.setattr("app.agents.supervisor.get_chat_model", no_key)
    events = events_of(ChatService(build_graph()), "hello")
    assert events == [{"type": "error", "message": "OPENAI_API_KEY is not set."}]


def test_reset_forgets_conversation(fake_llm):
    fake_llm([AIMessage(content='{"intent": "policy_qa"}'), AIMessage(content="Hi!")])
    graph = build_graph()
    service = ChatService(graph)
    events_of(service, "hello", session="to-reset")
    config = {"configurable": {"thread_id": "to-reset"}}
    assert graph.get_state(config).values["messages"]

    service.reset("to-reset")
    assert not graph.get_state(config).values
