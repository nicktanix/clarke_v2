"""clarke_ingest_skill tool — ingest a skill definition into CLARKE."""

import json

from clarke.mcp.tools import register
from clarke.mcp.tools._base import clarke_api


async def handle_ingest_skill(args: dict) -> str:
    """Ingest a skill definition for agent use."""
    payload: dict = {
        "tenant_id": args["tenant_id"],
        "project_id": args["project_id"],
        "skill_name": args["skill_name"],
        "content": args["content"],
    }
    for optional in ("trigger_conditions", "tool_access", "agent_capabilities", "priority"):
        if args.get(optional) is not None:
            payload[optional] = args[optional]

    result = await clarke_api("POST", "/agents/skills", json=payload)
    return json.dumps(result) if isinstance(result, dict) else result


register(
    {
        "name": "clarke_ingest_skill",
        "description": (
            "Ingest a skill definition into CLARKE. Skills define reusable "
            "capabilities that agents can invoke based on trigger conditions."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "tenant_id": {"type": "string", "description": "Tenant ID"},
                "project_id": {"type": "string", "description": "Project ID"},
                "skill_name": {
                    "type": "string",
                    "description": "Name of the skill",
                },
                "content": {
                    "type": "string",
                    "description": "Skill content (instructions, templates, etc.)",
                },
                "trigger_conditions": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Conditions under which this skill should activate",
                },
                "tool_access": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Tools this skill requires",
                },
                "agent_capabilities": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Required agent capabilities to use this skill",
                },
                "priority": {
                    "type": "integer",
                    "description": "Skill priority (higher = preferred)",
                },
            },
            "required": ["tenant_id", "project_id", "skill_name", "content"],
        },
    },
    handle_ingest_skill,
)
