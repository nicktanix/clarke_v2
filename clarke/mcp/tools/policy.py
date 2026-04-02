"""Policy tools — create, list, approve, and reject policies."""

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
        "auto_approve": args.get("auto_approve", True),
    }
    result = await clarke_api("POST", "/policy", json=payload)
    return json.dumps(result) if isinstance(result, (dict, list)) else result


register(
    {
        "name": "clarke_create_policy",
        "description": (
            "Create a new policy in CLARKE. Policies define canonical rules and "
            "constraints that take highest precedence in the trust ordering. "
            "By default, policies are auto-approved and immediately active."
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
                "auto_approve": {
                    "type": "boolean",
                    "description": "If true (default), policy is immediately active. If false, requires approval.",
                    "default": True,
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
    if "status" in args:
        params["status"] = args["status"]
    result = await clarke_api("GET", "/policy", params=params)
    return json.dumps(result) if isinstance(result, (dict, list)) else result


register(
    {
        "name": "clarke_list_policies",
        "description": (
            "List policies for a tenant. Filter by status: "
            "'active' (default), 'draft', 'pending_approval'."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "tenant_id": {"type": "string", "description": "Tenant ID"},
                "status": {
                    "type": "string",
                    "description": "Filter by status (active, draft, pending_approval)",
                    "enum": ["active", "draft", "pending_approval"],
                },
            },
            "required": ["tenant_id"],
        },
    },
    handle_list_policies,
)


# --- clarke_approve_policy ---


async def handle_approve_policy(args: dict) -> str:
    """Approve a pending policy."""
    payload: dict = {
        "approver_id": args["approver_id"],
        "comment": args.get("comment"),
    }
    result = await clarke_api(
        "POST", f"/policy/{args['policy_id']}/approve", json=payload
    )
    return json.dumps(result) if isinstance(result, (dict, list)) else result


register(
    {
        "name": "clarke_approve_policy",
        "description": (
            "Approve a pending policy, making it active. "
            "Use clarke_list_policies with status='draft' or 'pending_approval' "
            "to find policies awaiting approval."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "policy_id": {
                    "type": "string",
                    "description": "ID of the policy to approve",
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
            "required": ["policy_id", "approver_id"],
        },
    },
    handle_approve_policy,
)


# --- clarke_reject_policy ---


async def handle_reject_policy(args: dict) -> str:
    """Reject a pending policy."""
    payload: dict = {
        "approver_id": args["approver_id"],
        "comment": args.get("comment"),
    }
    result = await clarke_api(
        "POST", f"/policy/{args['policy_id']}/reject", json=payload
    )
    return json.dumps(result) if isinstance(result, (dict, list)) else result


register(
    {
        "name": "clarke_reject_policy",
        "description": "Reject a pending policy, returning it to draft status.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "policy_id": {
                    "type": "string",
                    "description": "ID of the policy to reject",
                },
                "approver_id": {
                    "type": "string",
                    "description": "ID of the rejecting user",
                },
                "comment": {
                    "type": "string",
                    "description": "Reason for rejection",
                },
            },
            "required": ["policy_id", "approver_id"],
        },
    },
    handle_reject_policy,
)
