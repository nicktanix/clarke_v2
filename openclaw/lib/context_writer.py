"""CLARKE context fetching utilities.

Used by the Python-side installer and bootstrap scripts. The actual
context injection for OpenClaw is handled by the native TypeScript plugin
(src/hooks/prompt-build.ts) which calls the same API endpoint.
"""

import sys

import httpx


def fetch_session_context(
    endpoint: str,
    tenant_id: str,
    project_id: str,
    agent_slug: str,
) -> str:
    """Fetch rendered session context from CLARKE API."""
    resp = httpx.post(
        f"{endpoint}/agents/session-context",
        json={
            "tenant_id": tenant_id,
            "project_id": project_id,
            "agent_slug": agent_slug,
            "format": "markdown",
        },
        timeout=30.0,
    )
    resp.raise_for_status()
    return resp.text


def fetch_session_greeting(endpoint: str, tenant_id: str) -> str:
    """Build a concise CLARKE status greeting."""
    status = "offline"
    agents = 0
    policies = 0

    try:
        health_resp = httpx.get(f"{endpoint}/health", timeout=5.0)
        if health_resp.status_code == 200:
            data = health_resp.json()
            status = data.get("status", "unknown")
    except (httpx.ConnectError, httpx.TimeoutException):
        return "CLARKE is offline | start with: make dev"

    try:
        agents_resp = httpx.get(
            f"{endpoint}/agents/profiles",
            params={"tenant_id": tenant_id, "status": "active"},
            timeout=5.0,
        )
        if agents_resp.status_code == 200:
            agents = len(agents_resp.json())
    except (httpx.ConnectError, httpx.HTTPStatusError):
        pass

    try:
        policy_resp = httpx.get(
            f"{endpoint}/policy",
            params={"tenant_id": tenant_id},
            timeout=5.0,
        )
        if policy_resp.status_code == 200:
            policies = len(policy_resp.json())
    except (httpx.ConnectError, httpx.HTTPStatusError):
        pass

    parts = [f"CLARKE is {status}"]

    stats = []
    if agents:
        stats.append(f"{agents} agent{'s' if agents != 1 else ''}")
    if policies:
        stats.append(f"{policies} {'policies' if policies != 1 else 'policy'}")
    if stats:
        parts.append(", ".join(stats))

    parts.append("/clarke for dashboard")

    return " | ".join(parts)


def refresh() -> None:
    """Print a CLARKE status greeting. Used by bootstrap scripts."""
    # Try to read connection info from environment
    import os

    endpoint = os.environ.get("CLARKE_API_URL", "http://localhost:8000")
    tenant_id = os.environ.get("CLARKE_TENANT_ID", "")

    if not tenant_id:
        print("No CLARKE_TENANT_ID set — skipping refresh", file=sys.stderr)
        return

    greeting = fetch_session_greeting(endpoint, tenant_id)
    print(greeting)
