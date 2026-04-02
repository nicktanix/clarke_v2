"""Agent profile tools — create, list, and update agent profiles."""

import json

from clarke.mcp.tools import register
from clarke.mcp.tools._base import clarke_api

# --- clarke_create_agent ---


async def handle_create_agent(args: dict) -> str:
    """Create a new agent profile in CLARKE."""
    payload: dict = {
        "tenant_id": args["tenant_id"],
        "project_id": args["project_id"],
        "name": args["name"],
        "slug": args["slug"],
        "model_id": args["model_id"],
    }
    for optional in (
        "capabilities",
        "tool_access",
        "budget_tokens",
        "behavioral_directives",
        "system_prompt_override",
        "allowed_sources",
    ):
        if args.get(optional) is not None:
            payload[optional] = args[optional]

    result = await clarke_api("POST", "/agents/profiles", json=payload)
    return json.dumps(result) if isinstance(result, (dict, list)) else result


register(
    {
        "name": "clarke_create_agent",
        "description": (
            "Create a new agent profile in CLARKE with identity, capabilities, "
            "model assignment, and behavioral directives."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "tenant_id": {"type": "string", "description": "Tenant ID"},
                "project_id": {"type": "string", "description": "Project ID"},
                "name": {
                    "type": "string",
                    "description": "Human-readable agent name",
                },
                "slug": {
                    "type": "string",
                    "description": "URL-safe agent slug (e.g., 'code-review')",
                },
                "model_id": {
                    "type": "string",
                    "description": "LiteLLM model identifier",
                },
                "capabilities": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of capability tags",
                },
                "tool_access": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of tools the agent may invoke",
                },
                "budget_tokens": {
                    "type": "integer",
                    "description": "Token budget for the agent",
                },
                "behavioral_directives": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Behavioral directive strings",
                },
                "system_prompt_override": {
                    "type": "string",
                    "description": "Override the default system prompt",
                },
                "allowed_sources": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Restrict retrieval to these source IDs",
                },
            },
            "required": ["tenant_id", "project_id", "name", "slug", "model_id"],
        },
    },
    handle_create_agent,
)


# --- clarke_list_agents ---


async def handle_list_agents(args: dict) -> str:
    """List agent profiles for a tenant."""
    params: dict = {
        "tenant_id": args["tenant_id"],
        "status": args.get("status", "active"),
    }
    result = await clarke_api("GET", "/agents/profiles", params=params)
    return json.dumps(result) if isinstance(result, (dict, list)) else result


register(
    {
        "name": "clarke_list_agents",
        "description": ("List all agent profiles for a tenant, optionally filtered by status."),
        "inputSchema": {
            "type": "object",
            "properties": {
                "tenant_id": {"type": "string", "description": "Tenant ID"},
                "status": {
                    "type": "string",
                    "description": "Filter by status (default: 'active')",
                },
            },
            "required": ["tenant_id"],
        },
    },
    handle_list_agents,
)


# --- clarke_update_agent ---


async def handle_update_agent(args: dict) -> str:
    """Update an existing agent profile."""
    profile_id = args["profile_id"]
    payload: dict = {}
    for field in (
        "name",
        "model_id",
        "capabilities",
        "tool_access",
        "budget_tokens",
        "behavioral_directives",
        "system_prompt_override",
        "allowed_sources",
    ):
        if args.get(field) is not None:
            payload[field] = args[field]

    result = await clarke_api("PUT", f"/agents/profiles/{profile_id}", json=payload)
    return json.dumps(result) if isinstance(result, (dict, list)) else result


register(
    {
        "name": "clarke_update_agent",
        "description": (
            "Update an existing agent profile's configuration, model, capabilities, or directives."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "profile_id": {
                    "type": "string",
                    "description": "Agent profile ID to update",
                },
                "name": {"type": "string", "description": "New agent name"},
                "model_id": {"type": "string", "description": "New model ID"},
                "capabilities": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Updated capabilities list",
                },
                "tool_access": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Updated tool access list",
                },
                "budget_tokens": {
                    "type": "integer",
                    "description": "Updated token budget",
                },
                "behavioral_directives": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Updated behavioral directives",
                },
                "system_prompt_override": {
                    "type": "string",
                    "description": "Updated system prompt override",
                },
                "allowed_sources": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Updated allowed source IDs",
                },
            },
            "required": ["profile_id"],
        },
    },
    handle_update_agent,
)
