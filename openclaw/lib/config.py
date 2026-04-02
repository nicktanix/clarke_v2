"""OpenClaw config manager — read/write openclaw.json."""

import json
import re
from pathlib import Path


def read_config(path: Path) -> dict:
    """Read openclaw.json, stripping JSON5 comments for compatibility."""
    text = path.read_text()
    # Strip single-line comments (// ...) but not inside strings
    cleaned = re.sub(r'(?<!:)//.*$', '', text, flags=re.MULTILINE)
    # Strip trailing commas before } or ]
    cleaned = re.sub(r',\s*([}\]])', r'\1', cleaned)
    return json.loads(cleaned)


def write_config(path: Path, config: dict) -> None:
    """Write openclaw.json with standard JSON formatting."""
    path.write_text(json.dumps(config, indent=2) + "\n")


def add_mcp_server(config: dict, agent_id: str, server_def: dict) -> dict:
    """Add a CLARKE MCP server to the specified agent's config."""
    agents = config.get("agents", {})
    agent_list = agents.get("list", [])

    for agent in agent_list:
        if agent.get("id") == agent_id:
            mcp = agent.setdefault("mcp", {})
            servers = mcp.setdefault("servers", [])

            # Check if CLARKE already registered
            for existing in servers:
                if existing.get("name") == server_def["name"]:
                    # Update in place
                    existing.update(server_def)
                    return config

            servers.append(server_def)
            return config

    # Agent not found — add to first agent or create one
    if agent_list:
        agent = agent_list[0]
        mcp = agent.setdefault("mcp", {})
        servers = mcp.setdefault("servers", [])
        servers.append(server_def)
    else:
        agent_list.append({
            "id": agent_id,
            "name": "CLARKE Agent",
            "mcp": {"servers": [server_def]},
        })
        agents["list"] = agent_list
        config["agents"] = agents

    return config


def get_clarke_mcp_server_def(endpoint: str = "http://localhost:8000") -> dict:
    """Build the CLARKE MCP server definition for openclaw.json."""
    return {
        "name": "clarke",
        "command": "python",
        "args": ["-m", "clarke.mcp.server"],
        "env": {"CLARKE_API_URL": endpoint},
    }
