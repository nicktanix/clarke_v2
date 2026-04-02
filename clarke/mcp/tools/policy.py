"""Policy tools — create and list policies."""

import json

from clarke.mcp.tools import register
from clarke.mcp.tools._base import clarke_api

# --- clarke_create_policy ---


async def handle_create_policy(args: dict) -> str:
    """Create a new policy in CLARKE."""
    payload: dict = {
        "tenant_id": args["tenant_id"],
        "content": args["content"],
        "owner_id": args["owner_id"],
    }
    result = await clarke_api("POST", "/policy", json=payload)
    return json.dumps(result) if isinstance(result, dict) else result


register(
    {
        "name": "clarke_create_policy",
        "description": (
            "Create a new policy in CLARKE. Policies define canonical rules and "
            "constraints that take highest precedence in the trust ordering."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "tenant_id": {"type": "string", "description": "Tenant ID"},
                "content": {
                    "type": "string",
                    "description": "Policy content (rules, constraints, guidelines)",
                },
                "owner_id": {
                    "type": "string",
                    "description": "ID of the policy owner",
                },
            },
            "required": ["tenant_id", "content", "owner_id"],
        },
    },
    handle_create_policy,
)


# --- clarke_list_policies ---


async def handle_list_policies(args: dict) -> str:
    """List policies for a tenant."""
    params: dict = {"tenant_id": args["tenant_id"]}
    result = await clarke_api("GET", "/policy", params=params)
    return json.dumps(result) if isinstance(result, dict) else result


register(
    {
        "name": "clarke_list_policies",
        "description": "List all policies for a tenant.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "tenant_id": {"type": "string", "description": "Tenant ID"},
            },
            "required": ["tenant_id"],
        },
    },
    handle_list_policies,
)
