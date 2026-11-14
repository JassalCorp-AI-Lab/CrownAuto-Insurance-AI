"""Chat use case: run one conversation turn through the graph.

`stream()` yields small progress events while the graph runs, so the UI can
show "Routed to Quote Agent → vehicle_lookup ✓ → ...". `send()` is the
blocking version that just returns the final reply.

Event types yielded by stream():
    {"type": "route",       "intent", "agent", "label"}
    {"type": "tool_call",   "agent", "name", "args"}
    {"type": "tool_result", "name", "ok"}
    {"type": "final",       "reply", "intent", "agent", "label", "tools_used"}
    {"type": "error",       "message"}
"""

import json
import logging
from typing import Iterator

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.errors import GraphRecursionError

from app.llm import MissingAPIKeyError

log = logging.getLogger(__name__)

AGENT_LABELS = {"quote": "Quote Agent", "claims": "Claims Agent", "policy_qa": "Policy Q&A Agent"}


class ChatError(RuntimeError):
    """A chat turn failed; the message is safe to show to the user."""


class ChatService:
    def __init__(self, graph, recursion_limit: int = 25):
        self._graph = graph
        self._recursion_limit = recursion_limit

    # ─── public API ───────────────────────────────────────────────────
    def stream(self, message: str, session_id: str, image_data_url: str | None = None) -> Iterator[dict]:
        """Run one turn and yield progress events (see module docstring)."""
        turn = _Turn()
        try:
            for chunk in self._graph.stream(
                self._input_state(message, image_data_url),
                config=self._config(session_id),
                stream_mode="updates",  # one chunk per node that finished
            ):
                for node, update in chunk.items():
                    yield from turn.handle(node, update or {})
        except MissingAPIKeyError as e:
            yield _error(str(e))
            return
        except GraphRecursionError:
            yield _error("The agent took too many steps on this request. Please rephrase or start a new chat.")
            return
        except Exception as e:  # bad key, unknown model, rate limit, network…
            log.exception("Chat turn failed")
            yield _error(f"{type(e).__name__}: {e}")
            return

        yield turn.final_event()

    def send(self, message: str, session_id: str, image_data_url: str | None = None) -> dict:
        """Run one turn and return the final event. Raises ChatError on failure."""
        for event in self.stream(message, session_id, image_data_url):
            if event["type"] == "error":
                raise ChatError(event["message"])
            if event["type"] == "final":
                return event
        raise ChatError("No reply was produced.")

    def reset(self, session_id: str) -> None:
        """Forget a conversation's saved state."""
        self._graph.checkpointer.delete_thread(session_id)

    # ─── helpers ──────────────────────────────────────────────────────
    def _config(self, session_id: str) -> dict:
        # thread_id tells the checkpointer which conversation to load/save.
        return {"configurable": {"thread_id": session_id}, "recursion_limit": self._recursion_limit}

    @staticmethod
    def _input_state(message: str, image_data_url: str | None) -> dict:
        state = {"messages": [HumanMessage(content=message)], "new_image": bool(image_data_url)}
        if image_data_url:
            state["damage_image_b64"] = image_data_url
        return state


class _Turn:
    """Collects what happened during one turn and converts graph updates to events."""

    def __init__(self):
        self.intent = None
        self.agent = None
        self.reply = ""
        self.tools_used: list[str] = []

    def handle(self, node: str, update: dict) -> Iterator[dict]:
        if node == "supervisor":
            self.intent, self.agent = update.get("intent"), update.get("next_agent")
            yield {"type": "route", "intent": self.intent, "agent": self.agent, "label": AGENT_LABELS.get(self.agent)}

        elif node in AGENT_LABELS:
            for msg in update.get("messages", []):
                if not isinstance(msg, AIMessage):
                    continue
                for call in msg.tool_calls or []:
                    self.tools_used.append(call["name"])
                    yield {"type": "tool_call", "agent": node, "name": call["name"], "args": _display_args(call["args"])}
                # .text joins the text blocks — newer models return a list of
                # content blocks (text, reasoning, ids…) instead of a plain string.
                if msg.text and not msg.tool_calls:
                    self.reply = msg.text

        elif node == "tools":
            for msg in update.get("messages", []):
                if isinstance(msg, ToolMessage):
                    yield {"type": "tool_result", "name": msg.name, "ok": _succeeded(msg.content)}

    def final_event(self) -> dict:
        return {
            "type": "final",
            "reply": self.reply or "Sorry — I couldn't produce a response. Please try again.",
            "intent": self.intent,
            "agent": self.agent,
            "label": AGENT_LABELS.get(self.agent),
            "tools_used": self.tools_used,
        }


def _error(message: str) -> dict:
    return {"type": "error", "message": message}


def _display_args(args: dict) -> dict:
    """Compact tool args for the UI — never echo image bytes."""
    shown = {}
    for key, value in args.items():
        if key == "image_b64":
            shown[key] = "<uploaded photo>"
        elif isinstance(value, str) and len(value) > 80:
            shown[key] = value[:77] + "…"
        else:
            shown[key] = value
    return shown


def _succeeded(tool_output: str) -> bool:
    try:
        data = json.loads(tool_output)
    except (TypeError, json.JSONDecodeError):
        return True
    return not (isinstance(data, dict) and "error" in data)
