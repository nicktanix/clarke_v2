"""Decision MCP tools — create and list structured decisions."""

import json

from clarke.mcp.tools import register
from clarke.mcp.tools._base import clarke_api


async def handle_create_decision(args: dict) -> str:
    """Record a structured decision in CLARKE."""
    payload: dict = {
        "tenant_id": args["tenant_id"],
        "project_id": args["project_id"],
        "title": args["title"],
        "rationale": args["rationale"],
        "decided_by": args["decided_by"],
    }
    if args.get("alternatives") is not None:
        payload["alternatives"] = args["alternatives"]

    result = await clarke_api("POST", "/decisions", json=payload)
    return json.dumps(result) if isinstance(result, (dict, list)) else result


async def handle_list_decisions(args: dict) -> str:
    """List decisions from CLARKE, with optional filtering."""
    params: dict = {
        "tenant_id": args["tenant_id"],
        "project_id": args["project_id"],
    }
    if args.get("status") is not None:
        params["status"] = args["status"]
    if args.get("search") is not None:
        params["search"] = args["search"]
    if args.get("limit") is not None:
        params["limit"] = args["limit"]
    if args.get("offset") is not None:
        params["offset"] = args["offset"]

    result = await clarke_api("GET", "/decisions", params=params)
    return json.dumps(result) if isinstance(result, (dict, list)) else result


register(
    {
        "name": "clarke_list_decisions",
        "description": (
            "List structured decisions recorded in CLARKE. Supports filtering "
            "by status and keyword search, with pagination."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "tenant_id": {"type": "string", "description": "Tenant ID"},
                "project_id": {"type": "string", "description": "Project ID"},
                "status": {
                    "type": "string",
                    "description": "Filter by decision status (default: 'active')",
                },
                "search": {
                    "type": "string",
                    "description": "Keyword to filter decisions by title or rationale",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results to return (default: 20)",
                    "minimum": 1,
                    "maximum": 100,
                },
                "offset": {
                    "type": "integer",
                    "description": "Number of results to skip for pagination (default: 0)",
                },
            },
            "required": ["tenant_id", "project_id"],
        },
    },
    handle_list_decisions,
)


register(
    {
        "name": "clarke_create_decision",
        "description": (
            "Record a structured decision in CLARKE. Decisions capture rationale "
            "and alternatives considered, and participate in the trust ordering "
            "for future context retrieval."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "tenant_id": {"type": "string", "description": "Tenant ID"},
                "project_id": {"type": "string", "description": "Project ID"},
                "title": {
                    "type": "string",
                    "description": "Decision title",
                },
                "rationale": {
                    "type": "string",
                    "description": "Why this decision was made",
                },
                "decided_by": {
                    "type": "string",
                    "description": "ID of the person or agent who made the decision",
                },
                "alternatives": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Alternatives that were considered",
                },
            },
            "required": [
                "tenant_id",
                "project_id",
                "title",
                "rationale",
                "decided_by",
            ],
        },
    },
    handle_create_decision,
)
