"""clarke_feedback tool — submit feedback on a CLARKE response."""

import json

from clarke.mcp.tools import register
from clarke.mcp.tools._base import clarke_api


async def handle_feedback(args: dict) -> str:
    """Submit feedback on a CLARKE response for the learning loop."""
    payload: dict = {
        "request_id": args["request_id"],
        "tenant_id": args["tenant_id"],
        "user_id": args["user_id"],
        "accepted": args["accepted"],
    }
    if args.get("score") is not None:
        payload["score"] = args["score"]
    if args.get("notes"):
        payload["notes"] = args["notes"]

    result = await clarke_api("POST", "/feedback", json=payload)
    return json.dumps(result) if isinstance(result, dict) else result


register(
    {
        "name": "clarke_feedback",
        "description": (
            "Submit feedback on a CLARKE response. This feeds the learning loop "
            "to improve retrieval quality and context relevance over time."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "request_id": {
                    "type": "string",
                    "description": "The request ID to provide feedback on",
                },
                "tenant_id": {"type": "string", "description": "Tenant ID"},
                "user_id": {"type": "string", "description": "User ID"},
                "accepted": {
                    "type": "boolean",
                    "description": "Whether the response was accepted/useful",
                },
                "score": {
                    "type": "number",
                    "description": "Optional numeric quality score (0.0-1.0)",
                },
                "notes": {
                    "type": "string",
                    "description": "Optional free-text feedback notes",
                },
            },
            "required": ["request_id", "tenant_id", "user_id", "accepted"],
        },
    },
    handle_feedback,
)
