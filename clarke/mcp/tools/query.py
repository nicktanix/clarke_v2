"""clarke_query tool — send a query through the CLARKE broker."""

import json

from clarke.mcp.tools import register
from clarke.mcp.tools._base import clarke_api


async def handle_query(args: dict) -> str:
    """Send a query through the CLARKE broker for context-augmented answering."""
    payload: dict = {
        "tenant_id": args["tenant_id"],
        "project_id": args["project_id"],
        "user_id": args["user_id"],
        "message": args["message"],
    }
    if args.get("session_id"):
        payload["session_id"] = args["session_id"]

    result = await clarke_api("POST", "/query", json=payload)
    return json.dumps(result) if isinstance(result, dict) else result


register(
    {
        "name": "clarke_query",
        "description": (
            "Send a query through the CLARKE broker for context-augmented answering. "
            "CLARKE retrieves relevant context from its knowledge base and returns "
            "a grounded response."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "tenant_id": {
                    "type": "string",
                    "description": "Tenant ID",
                },
                "project_id": {
                    "type": "string",
                    "description": "Project ID",
                },
                "user_id": {
                    "type": "string",
                    "description": "User ID",
                },
                "message": {
                    "type": "string",
                    "description": "The query message",
                },
                "session_id": {
                    "type": "string",
                    "description": ("Optional session ID for context continuity across queries"),
                },
            },
            "required": ["tenant_id", "project_id", "user_id", "message"],
        },
    },
    handle_query,
)
