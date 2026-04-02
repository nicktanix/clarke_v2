"""clarke_health tool — check CLARKE API health."""

import json

from clarke.mcp.tools import register
from clarke.mcp.tools._base import clarke_api


async def handle_health(args: dict) -> str:
    """Check CLARKE API health status."""
    result = await clarke_api("GET", "/health")
    return json.dumps(result) if isinstance(result, (dict, list)) else result


register(
    {
        "name": "clarke_health",
        "description": (
            "Check the health status of the CLARKE API and its dependencies "
            "(database, Qdrant, etc.)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
    handle_health,
)
