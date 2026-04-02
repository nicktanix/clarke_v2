#!/usr/bin/env python3
"""Claude Code session-start hook for CLARKE dynamic context.

Reads a minimal AGENTS.md stub to extract CLARKE connection info,
calls the session-context endpoint, and outputs the rendered markdown
to stdout for injection into the agent's system prompt.

Minimal AGENTS.md format:
    ---
    clarke_endpoint: http://localhost:8000
    agent_slug: code-review
    tenant_id: <uuid>
    project_id: <uuid>
    ---
    # Agent: Code Review Agent
    (optional static identity notes)

Usage as a Claude Code hook in settings.json:
    {
        "hooks": {
            "SessionStart": [{
                "type": "command",
                "command": "python scripts/cc_session_hook.py"
            }]
        }
    }

The script reads AGENTS.md from the current working directory.
"""

import sys
from pathlib import Path

import httpx
import yaml


def parse_agents_md(path: Path) -> dict:
    """Extract CLARKE config from AGENTS.md frontmatter."""
    content = path.read_text()

    # Parse YAML frontmatter between --- delimiters
    if not content.startswith("---"):
        print("AGENTS.md missing YAML frontmatter", file=sys.stderr)
        sys.exit(1)

    parts = content.split("---", 2)
    if len(parts) < 3:
        print("AGENTS.md frontmatter not properly delimited", file=sys.stderr)
        sys.exit(1)

    frontmatter = yaml.safe_load(parts[1])
    if not frontmatter:
        print("AGENTS.md frontmatter is empty", file=sys.stderr)
        sys.exit(1)

    required = ["clarke_endpoint", "agent_slug", "tenant_id", "project_id"]
    missing = [k for k in required if k not in frontmatter]
    if missing:
        print(f"AGENTS.md missing required fields: {', '.join(missing)}", file=sys.stderr)
        sys.exit(1)

    return frontmatter


def fetch_session_context(config: dict, task_context: str | None = None) -> str:
    """Call CLARKE session-context endpoint and return markdown."""
    payload = {
        "tenant_id": config["tenant_id"],
        "project_id": config["project_id"],
        "agent_slug": config["agent_slug"],
        "format": "markdown",
    }
    if task_context:
        payload["task_context"] = task_context

    endpoint = config["clarke_endpoint"].rstrip("/")
    response = httpx.post(
        f"{endpoint}/agents/session-context",
        json=payload,
        timeout=30.0,
    )
    response.raise_for_status()
    return response.text


def fetch_greeting(config: dict) -> str:
    """Build a concise CLARKE status line for session start."""
    endpoint = config["clarke_endpoint"].rstrip("/")
    tenant_id = config["tenant_id"]
    status = "offline"
    agents = 0
    policies = 0

    try:
        resp = httpx.get(f"{endpoint}/health", timeout=5.0)
        if resp.status_code == 200:
            status = resp.json().get("status", "unknown")
    except (httpx.ConnectError, httpx.TimeoutException):
        return "CLARKE is offline | start with: make dev"

    try:
        resp = httpx.get(
            f"{endpoint}/agents/profiles",
            params={"tenant_id": tenant_id, "status": "active"},
            timeout=5.0,
        )
        if resp.status_code == 200:
            agents = len(resp.json())
    except (httpx.ConnectError, httpx.HTTPStatusError):
        pass

    try:
        resp = httpx.get(f"{endpoint}/policy", params={"tenant_id": tenant_id}, timeout=5.0)
        if resp.status_code == 200:
            policies = len(resp.json())
    except (httpx.ConnectError, httpx.HTTPStatusError):
        pass

    parts = [f"CLARKE is {status}"]
    stats = []
    if agents:
        stats.append(f"{agents} agent{'s' if agents != 1 else ''}")
    if policies:
        stats.append(f"{policies} {'policies' if policies != 1 else 'policy'}")
    if stats:
        parts.append(" | ".join(stats))
    parts.append("/clarke for dashboard")
    return " | ".join(parts)


def main() -> None:
    agents_md = Path("AGENTS.md")
    if not agents_md.exists():
        # No AGENTS.md — nothing to inject, exit silently
        sys.exit(0)

    config = parse_agents_md(agents_md)

    # Optional: task context from environment or stdin
    task_context = None
    if len(sys.argv) > 1:
        task_context = " ".join(sys.argv[1:])

    try:
        context = fetch_session_context(config, task_context)
        # Output context for system prompt injection
        print(context)
        # Output greeting to stderr so it shows in the session start message
        greeting = fetch_greeting(config)
        print(greeting, file=sys.stderr)
    except httpx.HTTPStatusError as e:
        print(f"CLARKE session-context request failed: {e}", file=sys.stderr)
        sys.exit(0)
    except httpx.ConnectError:
        print("CLARKE is offline | start with: make dev", file=sys.stderr)
        sys.exit(0)


if __name__ == "__main__":
    main()
