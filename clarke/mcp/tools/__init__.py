"""Tool registry for CLARKE MCP server.

Each tool module calls ``register()`` at import time to add its tools.
After all modules are imported, ``TOOL_REGISTRY`` contains every tool
mapping name -> (schema, async_handler).
"""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from typing import Any

TOOL_REGISTRY: dict[str, tuple[dict, Callable[..., Coroutine[Any, Any, str]]]] = {}


def register(schema: dict, handler: Callable[..., Coroutine[Any, Any, str]]) -> None:
    """Register a tool schema and its async handler."""
    TOOL_REGISTRY[schema["name"]] = (schema, handler)


# Import all tool modules so they self-register.
from clarke.mcp.tools import (  # noqa: E402, F401
    agents,
    decisions,
    directives,
    feedback,
    health,
    ingest,
    policy,
    query,
    session_context,
    skills,
)
