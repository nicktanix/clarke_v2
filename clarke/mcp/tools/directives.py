"""Directive proposal tools — list, approve, and reject directive proposals."""

import json

from clarke.mcp.tools import register
from clarke.mcp.tools._base import clarke_api

# --- clarke_list_directives ---


async def handle_list_directives(args: dict) -> str:
    """List directive proposals for an agent profile."""
    profile_id = args["profile_id"]
    params: dict = {}
    if args.get("status"):
        params["status"] = args["status"]

    result = await clarke_api(
        "GET",
        f"/agents/profiles/{profile_id}/directives/proposals",
        params=params,
    )
    return json.dumps(result) if isinstance(result, (dict, list)) else result


register(
    {
        "name": "clarke_list_directives",
        "description": (
            "List directive proposals for an agent profile, optionally filtered "
            "by status (pending, approved, rejected)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "profile_id": {
                    "type": "string",
                    "description": "Agent profile ID",
                },
                "status": {
                    "type": "string",
                    "description": "Filter by proposal status (e.g., 'pending')",
                },
            },
            "required": ["profile_id"],
        },
    },
    handle_list_directives,
)


# --- clarke_approve_directive ---


async def handle_approve_directive(args: dict) -> str:
    """Approve a directive proposal."""
    profile_id = args["profile_id"]
    proposal_id = args["proposal_id"]
    payload: dict = {"approver_id": args["approver_id"]}
    if args.get("comment"):
        payload["comment"] = args["comment"]

    result = await clarke_api(
        "POST",
        f"/agents/profiles/{profile_id}/directives/proposals/{proposal_id}/approve",
        json=payload,
    )
    return json.dumps(result) if isinstance(result, (dict, list)) else result


register(
    {
        "name": "clarke_approve_directive",
        "description": (
            "Approve a pending directive proposal for an agent profile. "
            "Once approved, the directive becomes active."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "profile_id": {
                    "type": "string",
                    "description": "Agent profile ID",
                },
                "proposal_id": {
                    "type": "string",
                    "description": "Directive proposal ID to approve",
                },
                "approver_id": {
                    "type": "string",
                    "description": "ID of the approving user",
                },
                "comment": {
                    "type": "string",
                    "description": "Optional approval comment",
                },
            },
            "required": ["profile_id", "proposal_id", "approver_id"],
        },
    },
    handle_approve_directive,
)


# --- clarke_reject_directive ---


async def handle_reject_directive(args: dict) -> str:
    """Reject a directive proposal."""
    profile_id = args["profile_id"]
    proposal_id = args["proposal_id"]
    payload: dict = {"approver_id": args["approver_id"]}
    if args.get("comment"):
        payload["comment"] = args["comment"]

    result = await clarke_api(
        "POST",
        f"/agents/profiles/{profile_id}/directives/proposals/{proposal_id}/reject",
        json=payload,
    )
    return json.dumps(result) if isinstance(result, (dict, list)) else result


register(
    {
        "name": "clarke_reject_directive",
        "description": ("Reject a pending directive proposal for an agent profile."),
        "inputSchema": {
            "type": "object",
            "properties": {
                "profile_id": {
                    "type": "string",
                    "description": "Agent profile ID",
                },
                "proposal_id": {
                    "type": "string",
                    "description": "Directive proposal ID to reject",
                },
                "approver_id": {
                    "type": "string",
                    "description": "ID of the rejecting user",
                },
                "comment": {
                    "type": "string",
                    "description": "Optional rejection reason",
                },
            },
            "required": ["profile_id", "proposal_id", "approver_id"],
        },
    },
    handle_reject_directive,
)
