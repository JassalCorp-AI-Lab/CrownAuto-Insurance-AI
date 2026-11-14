"""Helpers for turning LLM text output into Python data."""

import json


def parse_json_response(content: str) -> dict:
    """Parse a JSON object from an LLM reply.

    LLMs sometimes wrap JSON in ```json fences even when told not to, so we
    strip those first. Raises json.JSONDecodeError if it still isn't JSON.
    """
    text = (content or "").strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    return json.loads(text)
