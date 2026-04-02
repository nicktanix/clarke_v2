"""clarke_session_context tool — fetch dynamic session context for an agent."""

import json

from clarke.mcp.tools import register
from clarke.mcp.tools._base import clarke_api


async def handle_session_context(args: dict) -> str:
    """Fetch dynamic session context from CLARKE."""
    payload: dict = {
        "agent_slug": args["agent_slug"],
        "tenant_id": args["tenant_id"],
        "project_id": args["project_id"],
        "format": args.get("format", "markdown"),
    }
    if args.get("task_context"):
        payload["task_context"] = args["task_context"]
    if args.get("session_id"):
        payload["session_id"] = args["session_id"]

    result = await clarke_api("POST", "/agents/session-context", json=payload)
    return json.dumps(result) if isinstance(result, (dict, list)) else result


register(
    {
        "name": "clarke_session_context",
        "description": (
            "Fetch dynamic session context for an agent from CLARKE. "
            "Returns the agent's full context including identity, directives, "
            "skills, policies, domain knowledge, and constraints."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "agent_slug": {
                    "type": "string",
                    "description": "Agent profile slug (e.g., 'code-review')",
                },
                "tenant_id": {
                    "type": "string",
                    "description": "Tenant ID for scoping",
                },
                "project_id": {
                    "type": "string",
                    "description": "Project ID for scoping",
                },
                "task_context": {
                    "type": "string",
                    "description": ("Optional task description for context-aware skill matching"),
                },
                "session_id": {
                    "type": "string",
                    "description": "Optional session ID for continuation",
                },
                "format": {
                    "type": "string",
                    "description": ("Response format — 'markdown' or 'json' (default: 'markdown')"),
                },
            },
            "required": ["agent_slug", "tenant_id", "project_id"],
        },
    },
    handle_session_context,
)
