"""Agents layer: the supervisor (router) and the three specialist agents.

An agent node is a function `(state) -> state updates`. It calls an LLM with
a system prompt and the conversation; the LLM may answer or request tools.
"""
