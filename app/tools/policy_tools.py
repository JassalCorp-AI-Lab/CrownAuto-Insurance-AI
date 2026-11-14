"""Tools for the Policy Q&A agent — RAG search."""

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from app.knowledge.vector_store import get_vector_store


class KBSearchInput(BaseModel):
    query: str = Field(description="Question or topic to search the policy knowledge base for")
    top_k: int = Field(default=3, description="Number of relevant chunks to retrieve")


@tool("policy_kb_search", args_schema=KBSearchInput)
def policy_kb_search(query: str, top_k: int = 3) -> dict:
    """Search the insurance policy and Canadian auto insurance rules knowledge base.

    Use this for any policy-related question: coverage, exclusions, claims-free
    discounts, deductibles, claim process, provincial rules, etc.
    """
    return {"query": query, "results": get_vector_store().search(query, top_k)}


POLICY_TOOLS = [policy_kb_search]
