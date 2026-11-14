"""The shared state that flows through the LangGraph workflow.

Every node receives this dict and returns *updates* to it. LangGraph saves it
after every step (checkpointing), keyed by the conversation's thread_id.
"""

from typing import Annotated, Literal, Optional, TypedDict

from langgraph.graph.message import add_messages

Intent = Literal["quote", "claim", "policy_qa"]

# Intent (what the user wants) → name of the agent node that handles it.
INTENT_TO_AGENT: dict[str, str] = {"quote": "quote", "claim": "claims", "policy_qa": "policy_qa"}


class AgentState(TypedDict, total=False):
    # `add_messages` APPENDS new messages instead of replacing the list.
    messages: Annotated[list, add_messages]

    # Routing — set by the supervisor each turn.
    intent: Optional[Intent]
    next_agent: Optional[str]

    # Latest uploaded damage photo as a data URL ("data:image/png;base64,...").
    damage_image_b64: Optional[str]
    # True only on the turn the photo was uploaded.
    new_image: bool
