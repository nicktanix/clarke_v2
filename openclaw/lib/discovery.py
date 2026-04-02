"""Workspace discovery — find OpenClaw config, existing content, and back up files."""

import shutil
from datetime import UTC, datetime
from pathlib import Path

import yaml


def find_workspace(start_path: Path | None = None) -> Path | None:
    """Find the OpenClaw agent workspace directory.

    OpenClaw stores agent files (SOUL.md, AGENTS.md, etc.) in a workspace/
    subdirectory under the config root. This function:
    1. Walks up from start_path looking for openclaw.json
    2. If found, checks for a workspace/ subdirectory containing SOUL.md
    3. Returns the workspace path (the directory with the actual agent files)
    """
    path = (start_path or Path.cwd()).resolve()

    # If start_path itself contains SOUL.md, it's the workspace
    if (path / "SOUL.md").exists():
        return path

    # Walk up looking for openclaw.json
    for parent in [path, *path.parents]:
        if (parent / "openclaw.json").exists():
            # Check for workspace/ subdirectory (standard OpenClaw layout)
            ws = parent / "workspace"
            if ws.exists() and (ws / "SOUL.md").exists():
                return ws
            # Fall back to the config root if no workspace/ subdir
            return parent

    return None


def find_openclaw_config(workspace: Path) -> Path | None:
    """Return path to openclaw.json — may be in workspace or its parent."""
    # Check the workspace itself
    config = workspace / "openclaw.json"
    if config.exists():
        return config
    # Check the parent (workspace/ is a subdirectory of the config root)
    config = workspace.parent / "openclaw.json"
    if config.exists():
        return config
    return None


def discover_existing_content(workspace: Path) -> dict[str, Path]:
    """Find existing agent files in the workspace."""
    files: dict[str, Path] = {}
    for name in ("SOUL.md", "AGENTS.md", "TOOLS.md", "USER.md"):
        path = workspace / name
        if path.exists():
            files[name] = path

    # Check for existing skills
    skills_dir = workspace / "skills"
    if skills_dir.exists():
        files["skills_dir"] = skills_dir

    # Check for existing hooks
    hooks_dir = workspace / "hooks"
    if hooks_dir.exists():
        files["hooks_dir"] = hooks_dir

    return files


def backup_workspace_files(workspace: Path, files: dict[str, Path]) -> Path:
    """Back up existing workspace files to .clarke-backup/ with timestamp."""
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
    backup_dir = workspace / ".clarke-backup" / timestamp
    backup_dir.mkdir(parents=True, exist_ok=True)

    for name, path in files.items():
        if name.endswith("_dir"):
            continue  # Skip directory references
        if path.exists():
            dest = backup_dir / name
            shutil.copy2(path, dest)
            print(f"  Backed up {name} -> {dest}")

    return backup_dir


def parse_soul_md(path: Path) -> dict:
    """Extract persona, directives, and knowledge from SOUL.md."""
    text = path.read_text()
    result: dict = {
        "raw_content": text,
        "name": "",
        "directives": [],
        "knowledge": [],
    }

    # Try YAML frontmatter
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            frontmatter = yaml.safe_load(parts[1]) or {}
            result["name"] = frontmatter.get("name", "")
            result["frontmatter"] = frontmatter

    # Extract sections
    lines = text.split("\n")
    current_section = ""
    for line in lines:
        if line.startswith("# "):
            result["name"] = result["name"] or line[2:].strip()
        elif line.startswith("## "):
            current_section = line[3:].strip().lower()
        elif line.startswith("- ") and current_section in ("directives", "rules", "principles"):
            result["directives"].append(line[2:].strip())
        elif line.startswith("- ") and current_section in ("knowledge", "context", "memory"):
            result["knowledge"].append(line[2:].strip())

    return result


def parse_agents_md(path: Path) -> dict:
    """Extract agent guidelines from AGENTS.md."""
    text = path.read_text()
    result: dict = {
        "raw_content": text,
        "guidelines": [],
    }

    lines = text.split("\n")
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("- ") and len(stripped) > 10:
            result["guidelines"].append(stripped[2:])

    return result
