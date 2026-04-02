#!/usr/bin/env python3
"""Bootstrap CLARKE with agent profiles, skill definitions, and Claude Code hooks.

Sources:
1. Local CLARKE skills from .claude/skills/clarke*
2. Superpowers skills + agents cloned from https://github.com/obra/superpowers

Seeds into CLARKE:
- Agent profiles (CLARKE operator + superpowers code-reviewer + any agents/*.md)
- Skills (local CLARKE skills + all superpowers skills/)
- Claude Code MCP configuration (.claude/.mcp.json)
- Claude Code hooks (.claude/settings.json)

Usage:
    python scripts/bootstrap_clarke_skills.py \
        --tenant-id <uuid> \
        --project-id <uuid> \
        --endpoint http://localhost:8000

Flags:
    --dry-run          Parse and validate only, don't call API
    --skip-api         Only verify files exist, don't seed API
    --skip-agent       Skip agent profile creation
    --skip-superpowers Skip cloning and ingesting superpowers
    --skip-hooks       Skip writing MCP config and hooks
    --superpowers-ref  Git ref for superpowers (default: main)
"""

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import httpx
import yaml

SKILLS_DIR = Path(".claude/skills")
SUPERPOWERS_REPO = "https://github.com/obra/superpowers.git"

# ──────────────────────────────────────────────────────────────────────
# Default CLARKE operator agent
# ──────────────────────────────────────────────────────────────────────

CLARKE_OPERATOR = {
    "name": "CLARKE Operator",
    "slug": "clarke-operator",
    "model_id": "claude-sonnet-4-20250514",
    "capabilities": [
        "clarke-admin",
        "skill-management",
        "policy-review",
        "document-ingestion",
        "memory-query",
    ],
    "tool_access": [
        "clarke_session_context",
        "clarke_query",
        "clarke_create_agent",
        "clarke_list_agents",
        "clarke_update_agent",
        "clarke_ingest_skill",
        "clarke_ingest_document",
        "clarke_create_policy",
        "clarke_list_policies",
        "clarke_list_directives",
        "clarke_approve_directive",
        "clarke_reject_directive",
        "clarke_health",
        "clarke_feedback",
        "clarke_create_decision",
    ],
    "budget_tokens": 16000,
    "behavioral_directives": [
        "You are the CLARKE system operator. You manage agent profiles, skills, policies, and the learning loop.",
        "Always confirm destructive operations (archive, reject) before executing.",
        "Show current state before asking for modifications.",
        "When ingesting content, verify the result status and suggest follow-up queries to test retrieval.",
        "Encourage users to provide feedback after queries to improve the learning loop.",
    ],
}

# Metadata for local CLARKE skills when ingested into Qdrant
CLARKE_SKILL_METADATA = {
    "clarke": {
        "trigger_conditions": ["CLARKE status", "show dashboard", "system health"],
        "agent_capabilities": ["clarke-admin"],
        "priority": 1,
    },
    "clarke-agent": {
        "trigger_conditions": ["create agent", "list agents", "update agent profile"],
        "agent_capabilities": ["clarke-admin", "skill-management"],
        "priority": 1,
    },
    "clarke-skill": {
        "trigger_conditions": ["create skill", "new skill", "teach capability"],
        "agent_capabilities": ["clarke-admin", "skill-management"],
        "priority": 1,
    },
    "clarke-teach": {
        "trigger_conditions": ["remember this", "record decision", "add policy", "correction"],
        "agent_capabilities": ["clarke-admin", "memory-query"],
        "priority": 1,
    },
    "clarke-recall": {
        "trigger_conditions": ["what does clarke know", "recall", "search memory"],
        "agent_capabilities": ["memory-query"],
        "priority": 1,
    },
    "clarke-review": {
        "trigger_conditions": ["review directives", "pending proposals", "what needs approval"],
        "agent_capabilities": ["clarke-admin", "policy-review"],
        "priority": 1,
    },
    "clarke-ingest": {
        "trigger_conditions": ["ingest file", "add document", "import to clarke"],
        "agent_capabilities": ["clarke-admin", "document-ingestion"],
        "priority": 1,
    },
    "clarke-configure": {
        "trigger_conditions": ["configure clarke", "show settings", "enable feature"],
        "agent_capabilities": ["clarke-admin"],
        "priority": 2,
    },
}

# Map superpowers skill names to CLARKE capabilities
SUPERPOWERS_CAPABILITY_MAP = {
    "brainstorming": ["planning", "design"],
    "dispatching-parallel-agents": ["orchestration", "multi-agent"],
    "executing-plans": ["planning", "implementation"],
    "finishing-a-development-branch": ["git", "devops"],
    "receiving-code-review": ["code_review"],
    "requesting-code-review": ["code_review"],
    "subagent-driven-development": ["orchestration", "implementation"],
    "systematic-debugging": ["debugging", "testing"],
    "test-driven-development": ["testing", "implementation"],
    "using-git-worktrees": ["git", "devops"],
    "using-superpowers": ["meta"],
    "verification-before-completion": ["testing", "quality"],
    "writing-plans": ["planning", "architecture"],
    "writing-skills": ["skill-management", "meta"],
}


# ──────────────────────────────────────────────────────────────────────
# Parsing helpers
# ──────────────────────────────────────────────────────────────────────


def parse_skill_file(path: Path) -> tuple[dict, str]:
    """Parse a SKILL.md file into (frontmatter, content body)."""
    text = path.read_text()
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    frontmatter = yaml.safe_load(parts[1]) or {}
    content = parts[2].strip()
    return frontmatter, content


def parse_agent_file(path: Path) -> tuple[dict, str]:
    """Parse a superpowers agent .md file into (frontmatter, system prompt body)."""
    text = path.read_text()
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    frontmatter = yaml.safe_load(parts[1]) or {}
    body = parts[2].strip()
    return frontmatter, body


# ──────────────────────────────────────────────────────────────────────
# Discovery
# ──────────────────────────────────────────────────────────────────────


def find_local_clarke_skills() -> list[tuple[str, Path]]:
    """Find local CLARKE skill files (clarke*) in .claude/skills/."""
    skills = []
    if not SKILLS_DIR.exists():
        return skills
    for skill_dir in sorted(SKILLS_DIR.iterdir()):
        if not skill_dir.is_dir():
            continue
        if not skill_dir.name.startswith("clarke"):
            continue
        skill_file = skill_dir / "SKILL.md"
        if skill_file.exists():
            skills.append((skill_dir.name, skill_file))
    return skills


def clone_superpowers(ref: str = "main") -> Path | None:
    """Clone superpowers repo to a temp directory. Returns path or None on failure."""
    tmpdir = Path(tempfile.mkdtemp(prefix="clarke_superpowers_"))
    try:
        subprocess.run(
            ["git", "clone", "--depth=1", f"--branch={ref}", SUPERPOWERS_REPO, str(tmpdir)],
            check=True,
            capture_output=True,
            text=True,
        )
        return tmpdir
    except subprocess.CalledProcessError as e:
        print(f"  Failed to clone superpowers: {e.stderr}", file=sys.stderr)
        shutil.rmtree(tmpdir, ignore_errors=True)
        return None
    except FileNotFoundError:
        print("  git not found — cannot clone superpowers", file=sys.stderr)
        shutil.rmtree(tmpdir, ignore_errors=True)
        return None


def find_superpowers_skills(repo_path: Path) -> list[tuple[str, Path]]:
    """Find all SKILL.md files in superpowers/skills/."""
    skills_dir = repo_path / "skills"
    skills = []
    if not skills_dir.exists():
        return skills
    for skill_dir in sorted(skills_dir.iterdir()):
        if not skill_dir.is_dir():
            continue
        skill_file = skill_dir / "SKILL.md"
        if skill_file.exists():
            skills.append((skill_dir.name, skill_file))
    return skills


def find_superpowers_agents(repo_path: Path) -> list[tuple[str, Path]]:
    """Find all agent .md files in superpowers/agents/."""
    agents_dir = repo_path / "agents"
    agents = []
    if not agents_dir.exists():
        return agents
    for agent_file in sorted(agents_dir.glob("*.md")):
        agents.append((agent_file.stem, agent_file))
    return agents


# ──────────────────────────────────────────────────────────────────────
# API operations
# ──────────────────────────────────────────────────────────────────────


def upsert_agent_profile(
    endpoint: str, tenant_id: str, project_id: str, agent_data: dict, dry_run: bool
) -> str | None:
    """Create or update an agent profile by slug."""
    slug = agent_data["slug"]
    try:
        resp = httpx.get(
            f"{endpoint}/agents/profiles",
            params={"tenant_id": tenant_id, "status": "active"},
            timeout=30.0,
        )
        resp.raise_for_status()
        for profile in resp.json():
            if profile.get("slug") == slug:
                if dry_run:
                    print(f"  [dry-run] Would update agent '{slug}' (id={profile['id']})")
                    return profile["id"]
                update_resp = httpx.put(
                    f"{endpoint}/agents/profiles/{profile['id']}",
                    json={
                        k: v
                        for k, v in agent_data.items()
                        if k
                        not in (
                            "slug",
                            "tenant_id",
                            "project_id",
                        )
                    },
                    timeout=30.0,
                )
                update_resp.raise_for_status()
                print(f"  Updated agent '{slug}' -> v{update_resp.json().get('version')}")
                return profile["id"]
    except httpx.ConnectError:
        print(f"  CLARKE not reachable — skipping agent '{slug}'", file=sys.stderr)
        return None
    except httpx.HTTPStatusError:
        pass

    if dry_run:
        print(f"  [dry-run] Would create agent '{agent_data['name']}'")
        return "dry-run-id"

    payload = {"tenant_id": tenant_id, "project_id": project_id, **agent_data}
    try:
        resp = httpx.post(f"{endpoint}/agents/profiles", json=payload, timeout=30.0)
        resp.raise_for_status()
        result = resp.json()
        print(f"  Created agent '{agent_data['name']}' -> {result['id']}")
        return result["id"]
    except httpx.HTTPStatusError as e:
        print(f"  Failed to create agent '{slug}': {e}", file=sys.stderr)
        return None


def ingest_skill(
    endpoint: str,
    tenant_id: str,
    project_id: str,
    skill_name: str,
    content: str,
    metadata: dict,
    dry_run: bool,
) -> bool:
    """Ingest a skill document into CLARKE."""
    payload = {
        "tenant_id": tenant_id,
        "project_id": project_id,
        "skill_name": skill_name,
        "content": content,
        "trigger_conditions": metadata.get("trigger_conditions", []),
        "tool_access": metadata.get("tool_access", []),
        "agent_capabilities": metadata.get("agent_capabilities", []),
        "priority": metadata.get("priority", 2),
    }

    if dry_run:
        print(f"  [dry-run] Would ingest skill '{skill_name}' ({len(content)} chars)")
        return True

    try:
        resp = httpx.post(f"{endpoint}/agents/skills", json=payload, timeout=60.0)
        resp.raise_for_status()
        result = resp.json()
        print(f"  Ingested skill '{skill_name}' -> doc={result['document_id']}")
        return True
    except httpx.HTTPStatusError as e:
        print(f"  Failed to ingest '{skill_name}': {e}", file=sys.stderr)
        return False
    except httpx.ConnectError:
        print(f"  CLARKE not reachable — skipping '{skill_name}'", file=sys.stderr)
        return False


# ──────────────────────────────────────────────────────────────────────
# Superpowers → CLARKE conversion
# ──────────────────────────────────────────────────────────────────────


def superpowers_agent_to_profile(name: str, frontmatter: dict, body: str) -> dict:
    """Convert a superpowers agent definition to a CLARKE AgentProfile dict."""
    description = frontmatter.get("description", "")
    # Extract a clean description from the potentially XML-heavy superpowers format
    if isinstance(description, str):
        # Take first sentence as a clean summary for behavioral directives
        desc_clean = description.split("<")[0].strip().split("\n")[0].strip()
    else:
        desc_clean = str(description)

    return {
        "name": name.replace("-", " ").title(),
        "slug": f"sp-{name}",
        "model_id": frontmatter.get("model", "claude-sonnet-4-20250514")
        if frontmatter.get("model") != "inherit"
        else "claude-sonnet-4-20250514",
        "system_prompt_override": body,
        "behavioral_directives": [desc_clean] if desc_clean else [],
        "capabilities": ["code_review", "quality"],
        "tool_access": [],
        "budget_tokens": 12000,
    }


def superpowers_skill_metadata(skill_name: str, frontmatter: dict) -> dict:
    """Build CLARKE skill metadata from superpowers skill frontmatter."""
    description = frontmatter.get("description", "")

    # Extract trigger conditions from description
    triggers = []
    if isinstance(description, str):
        # The description often contains "Use when:" patterns
        triggers.append(description[:200])

    capabilities = SUPERPOWERS_CAPABILITY_MAP.get(skill_name, ["general"])

    return {
        "trigger_conditions": triggers,
        "agent_capabilities": capabilities,
        "priority": 2,  # Superpowers skills are secondary to CLARKE-native skills
    }


# ──────────────────────────────────────────────────────────────────────
# Claude Code configuration (MCP + hooks)
# ──────────────────────────────────────────────────────────────────────


def configure_claude_code(
    endpoint: str,
    tenant_id: str,
    project_id: str,
    dry_run: bool,
) -> None:
    """Write ~/.claude/.mcp.json and ~/.claude/settings.json with CLARKE config (global scope)."""
    claude_dir = Path.home() / ".claude"
    claude_dir.mkdir(exist_ok=True)

    # ── MCP server config (global) ─────────────────────────────────
    mcp_path = claude_dir / ".mcp.json"
    mcp_config = {
        "mcpServers": {
            "clarke": {
                "command": "python",
                "args": ["-m", "clarke.mcp.server"],
                "env": {
                    "CLARKE_API_URL": endpoint,
                },
            }
        }
    }

    if mcp_path.exists():
        existing = json.loads(mcp_path.read_text())
        if "mcpServers" in existing and "clarke" in existing["mcpServers"]:
            print(f"  MCP config already has 'clarke' in {mcp_path}")
            # Update endpoint in case it changed
            existing["mcpServers"]["clarke"]["env"]["CLARKE_API_URL"] = endpoint
            mcp_config = existing
        else:
            # Merge: keep existing servers, add clarke
            existing.setdefault("mcpServers", {})
            existing["mcpServers"]["clarke"] = mcp_config["mcpServers"]["clarke"]
            mcp_config = existing

    if dry_run:
        print(f"  [dry-run] Would write MCP config to {mcp_path}")
    else:
        mcp_path.write_text(json.dumps(mcp_config, indent=2) + "\n")
        print(f"  Wrote MCP config -> {mcp_path}")

    # ── Hooks config (global) ─────────────────────────────────────
    settings_path = claude_dir / "settings.json"
    hook_command = "python scripts/cc_session_hook.py"

    hooks_config = {
        "hooks": {
            "SessionStart": [
                {
                    "matcher": "",
                    "hooks": [
                        {
                            "type": "command",
                            "command": hook_command,
                        }
                    ],
                }
            ],
            "PostToolUse": [
                {
                    "matcher": "Bash",
                    "if": "Bash(git commit*)",
                    "hooks": [
                        {
                            "type": "command",
                            "command": "npx gitnexus analyze 2>/dev/null || true",
                        }
                    ],
                }
            ],
        }
    }

    if settings_path.exists():
        existing = json.loads(settings_path.read_text())
        # Merge hooks: preserve existing non-CLARKE hooks
        existing_hooks = existing.get("hooks", {})

        # Update SessionStart: add CLARKE hook if not already present
        session_hooks = existing_hooks.get("SessionStart", [])
        clarke_hook_exists = any(
            hook_command in (h.get("command", "") for h in entry.get("hooks", []))
            for entry in session_hooks
        )
        if not clarke_hook_exists:
            session_hooks.append(hooks_config["hooks"]["SessionStart"][0])
        existing_hooks["SessionStart"] = session_hooks

        # Update PostToolUse: add gitnexus hook if not already present
        post_hooks = existing_hooks.get("PostToolUse", [])
        gitnexus_exists = any(
            "gitnexus" in (h.get("command", "") for h in entry.get("hooks", []))
            for entry in post_hooks
        )
        if not gitnexus_exists:
            post_hooks.append(hooks_config["hooks"]["PostToolUse"][0])
        existing_hooks["PostToolUse"] = post_hooks

        existing["hooks"] = existing_hooks
        hooks_config = existing

    if dry_run:
        print(f"  [dry-run] Would write hooks config to {settings_path}")
    else:
        settings_path.write_text(json.dumps(hooks_config, indent=2) + "\n")
        print(f"  Wrote hooks config -> {settings_path}")

    # ── AGENTS.md stub ──────────────────────────────────────────────
    agents_md = Path("AGENTS.md")
    stub = f"""---
clarke_endpoint: {endpoint}
agent_slug: clarke-operator
tenant_id: {tenant_id}
project_id: {project_id}
---
# CLARKE Operator
Context is dynamically loaded from CLARKE at session start.
Use /clarke for system status. Use /clarke-agent to manage agent profiles.
"""
    if agents_md.exists():
        # Check if already a CLARKE stub
        content = agents_md.read_text()
        if "clarke_endpoint" in content:
            print("  AGENTS.md already configured for CLARKE")
        else:
            backup = Path("AGENTS.md.backup")
            if dry_run:
                print(f"  [dry-run] Would backup AGENTS.md -> {backup}")
                print("  [dry-run] Would write CLARKE stub to AGENTS.md")
            else:
                shutil.copy2(agents_md, backup)
                print(f"  Backed up AGENTS.md -> {backup}")
                agents_md.write_text(stub)
                print("  Wrote CLARKE stub -> AGENTS.md")
    else:
        if dry_run:
            print("  [dry-run] Would write CLARKE stub to AGENTS.md")
        else:
            agents_md.write_text(stub)
            print("  Wrote CLARKE stub -> AGENTS.md")


# ──────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(description="Bootstrap CLARKE with skills and agent profiles")
    parser.add_argument("--tenant-id", required=True, help="Tenant ID")
    parser.add_argument("--project-id", required=True, help="Project ID")
    parser.add_argument("--endpoint", default="http://localhost:8000", help="CLARKE API endpoint")
    parser.add_argument("--dry-run", action="store_true", help="Validate only, don't call API")
    parser.add_argument("--skip-api", action="store_true", help="Skip all API calls")
    parser.add_argument("--skip-agent", action="store_true", help="Skip agent creation")
    parser.add_argument("--skip-superpowers", action="store_true", help="Skip superpowers clone")
    parser.add_argument("--skip-hooks", action="store_true", help="Skip MCP/hooks/AGENTS.md config")
    parser.add_argument(
        "--superpowers-ref", default="main", help="Git ref for superpowers (default: main)"
    )
    args = parser.parse_args()

    print("=== CLARKE Skills Bootstrap ===\n")

    # ── 0. Configure Claude Code (MCP + hooks + AGENTS.md) ─────────
    if not args.skip_hooks:
        print("--- Claude Code Configuration ---")
        configure_claude_code(args.endpoint, args.tenant_id, args.project_id, args.dry_run)

    agents_to_create: list[dict] = []
    skills_to_ingest: list[tuple[str, str, dict]] = []  # (name, content, metadata)

    # ── 1. Local CLARKE skills ──────────────────────────────────────
    local_skills = find_local_clarke_skills()
    print(f"Local CLARKE skills: {len(local_skills)}")
    for name, path in local_skills:
        _fm, content = parse_skill_file(path)
        metadata = CLARKE_SKILL_METADATA.get(name, {"agent_capabilities": ["clarke-admin"]})
        skills_to_ingest.append((name, content, metadata))
        print(f"  - {name}")

    # ── 2. CLARKE operator agent ────────────────────────────────────
    if not args.skip_agent:
        agents_to_create.append(CLARKE_OPERATOR)

    # ── 3. Superpowers ──────────────────────────────────────────────
    sp_dir = None
    if not args.skip_superpowers:
        print(f"\nCloning superpowers ({args.superpowers_ref})...")
        sp_dir = clone_superpowers(args.superpowers_ref)

    if sp_dir:
        # Agents
        sp_agents = find_superpowers_agents(sp_dir)
        print(f"\nSuperpowers agents: {len(sp_agents)}")
        for name, path in sp_agents:
            fm, body = parse_agent_file(path)
            profile = superpowers_agent_to_profile(name, fm, body)
            agents_to_create.append(profile)
            print(f"  - {name} -> slug: {profile['slug']}")

        # Skills
        sp_skills = find_superpowers_skills(sp_dir)
        print(f"\nSuperpowers skills: {len(sp_skills)}")
        for name, path in sp_skills:
            fm, content = parse_skill_file(path)
            metadata = superpowers_skill_metadata(name, fm)
            skills_to_ingest.append((f"sp-{name}", content, metadata))
            print(f"  - {name} -> sp-{name}")

    # ── Summary before API calls ────────────────────────────────────
    print(f"\nTotal: {len(agents_to_create)} agents, {len(skills_to_ingest)} skills")

    if args.skip_api:
        print("\n--skip-api: Skipping all API calls")
        if sp_dir:
            shutil.rmtree(sp_dir, ignore_errors=True)
        return

    # ── 4. Create/update agents ─────────────────────────────────────
    if not args.skip_agent and agents_to_create:
        print("\n--- Agent Profiles ---")
        for agent in agents_to_create:
            upsert_agent_profile(
                args.endpoint, args.tenant_id, args.project_id, agent, args.dry_run
            )

    # ── 5. Ingest skills ────────────────────────────────────────────
    print("\n--- Skills Ingestion ---")
    ingested = 0
    failed = 0
    for name, content, metadata in skills_to_ingest:
        if ingest_skill(
            args.endpoint, args.tenant_id, args.project_id, name, content, metadata, args.dry_run
        ):
            ingested += 1
        else:
            failed += 1

    # ── Cleanup ─────────────────────────────────────────────────────
    if sp_dir:
        shutil.rmtree(sp_dir, ignore_errors=True)

    # ── Report ──────────────────────────────────────────────────────
    print("\n--- Summary ---")
    print(f"  Agents created/updated: {len(agents_to_create)}")
    print(f"  Skills ingested: {ingested}")
    if failed:
        print(f"  Skills failed: {failed}")
    print("\nDone. Use '/clarke' in Claude Code to verify.")


if __name__ == "__main__":
    main()
