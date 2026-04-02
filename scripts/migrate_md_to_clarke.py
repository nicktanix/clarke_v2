#!/usr/bin/env python3
"""Migrate static AGENTS.md / SKILLS.md files into CLARKE dynamic context.

Parses existing agent configuration files and:
1. Creates AgentProfile records via the CLARKE API
2. Ingests skill definitions via the skill ingestion endpoint
3. Generates a minimal replacement AGENTS.md stub

Usage:
    python scripts/migrate_md_to_clarke.py \
        --agents-md path/to/AGENTS.md \
        --skills-dir path/to/skills/ \
        --tenant-id <uuid> \
        --project-id <uuid> \
        --endpoint http://localhost:8000
"""

import argparse
import re
import sys
from pathlib import Path

import httpx
import yaml


def parse_agents_md(path: Path) -> list[dict]:
    """Parse AGENTS.md into a list of agent definitions.

    Supports two formats:
    1. YAML frontmatter with agent definitions
    2. Markdown sections with ## Agent: <name> headings
    """
    content = path.read_text()
    agents = []

    # Try YAML frontmatter first
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            frontmatter = yaml.safe_load(parts[1])
            if isinstance(frontmatter, dict) and "agents" in frontmatter:
                return frontmatter["agents"]

    # Fall back to markdown section parsing
    sections = re.split(r"^##\s+", content, flags=re.MULTILINE)
    for section in sections[1:]:  # Skip content before first ##
        lines = section.strip().split("\n")
        header = lines[0].strip()

        # Extract agent name from header
        name_match = re.match(r"(?:Agent:\s*)?(.+)", header)
        if not name_match:
            continue

        name = name_match.group(1).strip()
        slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
        body = "\n".join(lines[1:]).strip()

        agent: dict = {
            "name": name,
            "slug": slug,
            "model_id": "claude-sonnet-4-20250514",
            "behavioral_directives": [],
            "capabilities": [],
            "tool_access": [],
        }

        # Extract structured fields from body
        for line in body.split("\n"):
            line = line.strip()
            if line.startswith("- **Model"):
                model_match = re.search(r":\s*(.+)", line)
                if model_match:
                    agent["model_id"] = model_match.group(1).strip().rstrip("*")
            elif line.startswith("- **Capabilities"):
                cap_match = re.search(r":\s*(.+)", line)
                if cap_match:
                    agent["capabilities"] = [
                        c.strip() for c in cap_match.group(1).strip().rstrip("*").split(",")
                    ]
            elif line.startswith("- **Tools"):
                tool_match = re.search(r":\s*(.+)", line)
                if tool_match:
                    agent["tool_access"] = [
                        t.strip() for t in tool_match.group(1).strip().rstrip("*").split(",")
                    ]
            elif line.startswith("- ") and not line.startswith("- **"):
                agent["behavioral_directives"].append(line[2:])

        agents.append(agent)

    return agents


def parse_skill_files(skills_dir: Path) -> list[dict]:
    """Parse skill definition files from a directory."""
    skills = []
    for md_file in sorted(skills_dir.glob("**/*.md")):
        content = md_file.read_text()
        name = md_file.stem

        # Try YAML frontmatter
        metadata: dict = {}
        skill_content = content
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                metadata = yaml.safe_load(parts[1]) or {}
                skill_content = parts[2].strip()

        skills.append(
            {
                "skill_name": metadata.get("name", name),
                "content": skill_content,
                "trigger_conditions": metadata.get("trigger_conditions", []),
                "tool_access": metadata.get("tool_access", []),
                "agent_capabilities": metadata.get("agent_capabilities", []),
                "priority": metadata.get("priority", 1),
            }
        )

    return skills


def create_profile(endpoint: str, tenant_id: str, project_id: str, agent: dict) -> dict:
    """Create an agent profile via the API."""
    payload = {
        "tenant_id": tenant_id,
        "project_id": project_id,
        "name": agent["name"],
        "slug": agent["slug"],
        "model_id": agent.get("model_id", "claude-sonnet-4-20250514"),
        "behavioral_directives": agent.get("behavioral_directives", []),
        "capabilities": agent.get("capabilities", []),
        "tool_access": agent.get("tool_access", []),
        "budget_tokens": agent.get("budget_tokens", 8000),
    }
    if agent.get("system_prompt_override"):
        payload["system_prompt_override"] = agent["system_prompt_override"]

    response = httpx.post(f"{endpoint}/agents/profiles", json=payload, timeout=30.0)
    response.raise_for_status()
    return response.json()


def ingest_skill(endpoint: str, tenant_id: str, project_id: str, skill: dict) -> dict:
    """Ingest a skill document via the API."""
    payload = {
        "tenant_id": tenant_id,
        "project_id": project_id,
        **skill,
    }
    response = httpx.post(f"{endpoint}/agents/skills", json=payload, timeout=60.0)
    response.raise_for_status()
    return response.json()


def generate_minimal_agents_md(
    endpoint: str, tenant_id: str, project_id: str, agents: list[dict]
) -> str:
    """Generate a minimal AGENTS.md stub for Claude Code."""
    sections = []
    for agent in agents:
        sections.append(f"""---
clarke_endpoint: {endpoint}
agent_slug: {agent["slug"]}
tenant_id: {tenant_id}
project_id: {project_id}
---
# Agent: {agent["name"]}
Context is dynamically loaded from CLARKE at session start.
""")
    return "\n".join(sections)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Migrate AGENTS.md / skills to CLARKE dynamic context"
    )
    parser.add_argument("--agents-md", type=Path, help="Path to AGENTS.md")
    parser.add_argument("--skills-dir", type=Path, help="Path to skills directory")
    parser.add_argument("--tenant-id", required=True, help="Tenant ID")
    parser.add_argument("--project-id", required=True, help="Project ID")
    parser.add_argument("--endpoint", default="http://localhost:8000", help="CLARKE API endpoint")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("AGENTS.md.minimal"),
        help="Output path for minimal AGENTS.md",
    )
    parser.add_argument("--dry-run", action="store_true", help="Parse only, don't call API")
    args = parser.parse_args()

    if not args.agents_md and not args.skills_dir:
        print("At least one of --agents-md or --skills-dir is required", file=sys.stderr)
        sys.exit(1)

    agents: list[dict] = []
    skills: list[dict] = []

    # Parse agents
    if args.agents_md and args.agents_md.exists():
        agents = parse_agents_md(args.agents_md)
        print(f"Parsed {len(agents)} agent(s) from {args.agents_md}")
        for a in agents:
            print(f"  - {a['name']} ({a['slug']})")

    # Parse skills
    if args.skills_dir and args.skills_dir.exists():
        skills = parse_skill_files(args.skills_dir)
        print(f"Parsed {len(skills)} skill(s) from {args.skills_dir}")
        for s in skills:
            print(f"  - {s['skill_name']}")

    if args.dry_run:
        print("\n[dry-run] Would create the above profiles and skills.")
        return

    # Create profiles
    for agent in agents:
        try:
            result = create_profile(args.endpoint, args.tenant_id, args.project_id, agent)
            print(f"Created profile: {agent['name']} -> {result['id']}")
        except httpx.HTTPStatusError as e:
            print(f"Failed to create profile {agent['name']}: {e}", file=sys.stderr)

    # Ingest skills
    for skill in skills:
        try:
            result = ingest_skill(args.endpoint, args.tenant_id, args.project_id, skill)
            print(f"Ingested skill: {skill['skill_name']} -> {result['document_id']}")
        except httpx.HTTPStatusError as e:
            print(f"Failed to ingest skill {skill['skill_name']}: {e}", file=sys.stderr)

    # Generate minimal AGENTS.md
    if agents:
        minimal = generate_minimal_agents_md(args.endpoint, args.tenant_id, args.project_id, agents)
        args.output.write_text(minimal)
        print(f"\nMinimal AGENTS.md written to {args.output}")
        print("Replace your existing AGENTS.md with this file to use dynamic context.")


if __name__ == "__main__":
    main()
