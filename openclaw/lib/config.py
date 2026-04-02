"""OpenClaw config manager — read/write openclaw.json."""

import json
import re
from pathlib import Path


def read_config(path: Path) -> dict:
    """Read openclaw.json, stripping JSON5 comments for compatibility."""
    text = path.read_text()
    # Strip single-line comments (// ...) but not inside strings
    cleaned = re.sub(r"(?<!:)//.*$", "", text, flags=re.MULTILINE)
    # Strip trailing commas before } or ]
    cleaned = re.sub(r",\s*([}\]])", r"\1", cleaned)
    return json.loads(cleaned)


def write_config(path: Path, config: dict) -> None:
    """Write openclaw.json with standard JSON formatting."""
    path.write_text(json.dumps(config, indent=2) + "\n")


def add_mcp_server(config: dict, server_name: str, server_def: dict) -> dict:
    """Add a CLARKE MCP server to the top-level mcp.servers config.

    OpenClaw expects MCP servers at the top level:
        { "mcp": { "servers": { "server-name": { "command": ..., "args": ... } } } }

    NOT under agents.list[].mcp (that key is not recognized).
    """
    mcp = config.setdefault("mcp", {})
    servers = mcp.setdefault("servers", {})

    # Add or update the server entry
    servers[server_name] = server_def

    return config


def get_clarke_mcp_server_def(
    endpoint: str = "http://localhost:8000",
    clarke_install_dir: str | None = None,
) -> dict:
    """Build the CLARKE MCP server definition for openclaw.json.

    Uses the absolute path to the CLARKE venv's Python binary so the
    MCP server works regardless of what 'python' resolves to on the system.
    """
    from pathlib import Path

    install_dir = Path(clarke_install_dir) if clarke_install_dir else Path.home() / ".clarke"
    venv_python = install_dir / ".venv" / "bin" / "python"

    # Fall back to python3 if venv doesn't exist (e.g., pip install -e was done globally)
    if not venv_python.exists():
        import shutil

        venv_python = Path(shutil.which("python3") or "python3")

    return {
        "command": str(venv_python),
        "args": ["-m", "clarke.mcp.server"],
        "env": {"CLARKE_API_URL": endpoint},
        "cwd": str(install_dir),
    }
