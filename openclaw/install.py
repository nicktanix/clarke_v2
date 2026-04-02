#!/usr/bin/env python3
"""One-shot CLARKE installer for OpenClaw.

Sets up the full CLARKE memory and context engine for an OpenClaw workspace:
1. Starts backend services (PostgreSQL, Qdrant, Neo4j)
2. Creates tenant and project
3. Discovers and backs up existing workspace content
4. Ingests existing SOUL.md/AGENTS.md into CLARKE
5. Registers CLARKE MCP server in openclaw.json
6. Installs CLARKE skills and hooks
7. Bootstraps agent profiles and superpowers skills
8. Writes CLARKE-augmented SOUL.md and AGENTS.md

Usage:
    python openclaw/install.py --workspace /path/to/openclaw/workspace

    # Or with CLARKE backend already running:
    python openclaw/install.py --workspace /path/to/workspace --skip-backend
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

import httpx

# Ensure the CLARKE repo is importable
CLARKE_REPO = Path(__file__).resolve().parent.parent
if str(CLARKE_REPO) not in sys.path:
    sys.path.insert(0, str(CLARKE_REPO))

from openclaw.lib.backend import (  # noqa: E402
    check_clarke_health,
    ensure_tenant_project,
    find_clarke_repo,
    run_migrations,
    start_api_server,
    start_backend,
)
from openclaw.lib.config import (  # noqa: E402
    add_mcp_server,
    get_clarke_mcp_server_def,
    read_config,
    write_config,
)
from openclaw.lib.discovery import (  # noqa: E402
    backup_workspace_files,
    discover_existing_content,
    find_openclaw_config,
    find_workspace,
    parse_soul_md,
)

PLUGIN_DIR = Path(__file__).resolve().parent


def install(args: argparse.Namespace) -> None:
    """Run the full installation."""
    print("=== CLARKE for OpenClaw — Installation ===\n")

    dry_run = args.dry_run
    endpoint = args.endpoint

    # ── 1. Find workspace ───────────────────────────────────────────
    print("--- Workspace Detection ---")
    workspace = Path(args.workspace).resolve() if args.workspace else None
    if not workspace:
        workspace = find_workspace()
    if not workspace:
        print("No OpenClaw workspace found. Specify --workspace or run from an OpenClaw directory.")
        sys.exit(1)
    print(f"  Workspace: {workspace}")

    # ── 2. Backend setup ────────────────────────────────────────────
    if not args.skip_backend:
        print("\n--- Backend Setup ---")
        clarke_repo = find_clarke_repo()
        print(f"  CLARKE repo: {clarke_repo}")

        if check_clarke_health(endpoint):
            print("  CLARKE backend already healthy")
        else:
            if dry_run:
                print("  [dry-run] Would start docker compose + migrations + API server")
            else:
                if not start_backend(clarke_repo):
                    print("  WARNING: Backend services may not be fully ready", file=sys.stderr)
                run_migrations(clarke_repo)
                start_api_server(clarke_repo, endpoint)

        if not dry_run and not check_clarke_health(endpoint):
            print(f"  CLARKE API not reachable at {endpoint}", file=sys.stderr)
            print("  Start it manually: make dev", file=sys.stderr)
            sys.exit(1)
    else:
        print("\n--- Backend Setup (skipped) ---")
        if not dry_run and not check_clarke_health(endpoint):
            print(f"  WARNING: CLARKE not reachable at {endpoint}", file=sys.stderr)

    # ── 3. Create tenant + project ──────────────────────────────────
    print("\n--- Tenant & Project ---")
    if dry_run:
        print("  [dry-run] Would create tenant/project")
        tenant_id = "dry-run-tenant-id"
        project_id = "dry-run-project-id"
    else:
        try:
            tenant_id, project_id = ensure_tenant_project(
                endpoint, args.tenant_name, args.project_name
            )
            print(f"  Tenant:  {tenant_id}")
            print(f"  Project: {project_id}")
        except (httpx.ConnectError, httpx.HTTPStatusError) as e:
            print(f"  Failed to create tenant/project: {e}", file=sys.stderr)
            sys.exit(1)

    # ── 4. Discover + backup existing content ───────────────────────
    print("\n--- Workspace Discovery ---")
    existing = discover_existing_content(workspace)
    if existing:
        found = [k for k in existing if not k.endswith("_dir")]
        print(f"  Found: {', '.join(found) if found else 'no agent files'}")

        if not dry_run and not args.skip_backup:
            backup_dir = backup_workspace_files(workspace, existing)
            print(f"  Backups in: {backup_dir}")
        elif dry_run:
            print("  [dry-run] Would back up existing files")
    else:
        print("  No existing agent files found")

    # ── 5. Ingest existing content into CLARKE ──────────────────────
    if not dry_run and not args.skip_backend:
        print("\n--- Ingesting Existing Content ---")
        _ingest_existing_content(workspace, existing, endpoint, tenant_id, project_id)

    # ── 6. Register MCP server in openclaw.json ─────────────────────
    print("\n--- MCP Registration ---")
    config_path = find_openclaw_config(workspace)
    if config_path:
        if dry_run:
            print(f"  [dry-run] Would add CLARKE MCP server to {config_path}")
        else:
            config = read_config(config_path)
            server_def = get_clarke_mcp_server_def(endpoint, str(CLARKE_REPO))
            config = add_mcp_server(config, "clarke", server_def)
            write_config(config_path, config)
            print(f"  Added CLARKE MCP server to {config_path}")
    else:
        print("  openclaw.json not found — skipping MCP registration")
        print("  You can manually add CLARKE MCP server to your config later")

    # ── 7. Install skills ───────────────────────────────────────────
    print("\n--- Installing Skills ---")
    skills_src = PLUGIN_DIR / "skills"
    skills_dst = workspace / "skills"
    skills_dst.mkdir(exist_ok=True)

    installed_skills = 0
    for skill_dir in sorted(skills_src.iterdir()):
        if not skill_dir.is_dir():
            continue
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.exists():
            continue

        dst_dir = skills_dst / skill_dir.name
        if dry_run:
            print(f"  [dry-run] Would install skill: {skill_dir.name}")
        else:
            dst_dir.mkdir(exist_ok=True)
            shutil.copy2(skill_file, dst_dir / "SKILL.md")
            print(f"  Installed skill: {skill_dir.name}")
        installed_skills += 1

    # ── 8. Build TypeScript plugin ────────────────────────────────
    print("\n--- Building Plugin ---")
    if dry_run:
        print("  [dry-run] Would run npm install && npm run build")
    else:
        try:
            subprocess.run(
                ["npm", "install"],
                cwd=PLUGIN_DIR,
                check=True,
                capture_output=True,
                text=True,
            )
            subprocess.run(
                ["npm", "run", "build"],
                cwd=PLUGIN_DIR,
                check=True,
                capture_output=True,
                text=True,
            )
            print("  TypeScript plugin built successfully")
        except subprocess.CalledProcessError as e:
            print(f"  Plugin build failed: {e.stderr[:200]}", file=sys.stderr)
            print("  Context injection will not work until the plugin is built", file=sys.stderr)
        except FileNotFoundError:
            print("  npm not found — skipping plugin build", file=sys.stderr)
            print("  Run: cd openclaw && npm install && npm run build", file=sys.stderr)

    # ── 9. Set environment for plugin ──────────────────────────────
    print("\n--- Configuring Plugin Environment ---")
    env_note = (
        f"  CLARKE_API_URL={endpoint}\n"
        f"  CLARKE_TENANT_ID={tenant_id}\n"
        f"  CLARKE_PROJECT_ID={project_id}\n"
        f"  CLARKE_AGENT_SLUG={args.agent_slug}"
    )
    if dry_run:
        print(f"  [dry-run] Plugin needs these env vars:\n{env_note}")
    else:
        print("  The plugin reads config from environment variables.")
        print(f"  Add these to your OpenClaw environment or .env:\n{env_note}")

    # ── 10. Bootstrap CLARKE (agents + skills into Qdrant) ──────────
    if not dry_run and not args.skip_backend:
        print("\n--- CLARKE Bootstrap ---")
        _bootstrap_clarke(endpoint, tenant_id, project_id, args.skip_superpowers)

    # ── Report ──────────────────────────────────────────────────────
    print("\n" + "=" * 50)
    print("CLARKE installation complete!")
    print(f"  Workspace:    {workspace}")
    print(f"  Endpoint:     {endpoint}")
    print(f"  Tenant:       {tenant_id}")
    print(f"  Project:      {project_id}")
    print(f"  Agent:        {args.agent_slug}")
    print(f"  Skills:       {installed_skills}")
    print()
    print("Next steps:")
    print("  1. Start your OpenClaw agent")
    print("  2. Try: /clarke (dashboard)")
    print("  3. Try: /clarke-recall 'what does CLARKE know'")
    print("  4. Try: /clarke-teach to record decisions and policies")


def _ingest_existing_content(
    workspace: Path,
    existing: dict[str, Path],
    endpoint: str,
    tenant_id: str,
    project_id: str,
) -> None:
    """Ingest existing SOUL.md/AGENTS.md content into CLARKE."""
    for name in ("SOUL.md", "AGENTS.md"):
        if name not in existing:
            continue
        path = existing[name]
        content = path.read_text()
        if not content.strip():
            continue

        # Ingest as a document
        try:
            resp = httpx.post(
                f"{endpoint}/ingest",
                json={
                    "tenant_id": tenant_id,
                    "project_id": project_id,
                    "filename": f"openclaw_{name.lower().replace('.', '_')}",
                    "content_type": "text/markdown",
                    "content": content,
                    "metadata": {
                        "source": "openclaw_migration",
                        "original_file": name,
                    },
                },
                timeout=60.0,
            )
            resp.raise_for_status()
            print(f"  Ingested {name} ({len(content)} chars)")
        except (httpx.ConnectError, httpx.HTTPStatusError) as e:
            print(f"  Failed to ingest {name}: {e}", file=sys.stderr)

    # If SOUL.md has structured persona, create an agent profile
    if "SOUL.md" in existing:
        soul_data = parse_soul_md(existing["SOUL.md"])
        if soul_data.get("name"):
            try:
                resp = httpx.post(
                    f"{endpoint}/agents/profiles",
                    json={
                        "tenant_id": tenant_id,
                        "project_id": project_id,
                        "name": soul_data["name"],
                        "slug": "openclaw-agent",
                        "model_id": "claude-sonnet-4-20250514",
                        "behavioral_directives": soul_data.get("directives", []),
                        "capabilities": ["general"],
                    },
                    timeout=30.0,
                )
                if resp.status_code in (200, 201):
                    print(f"  Created agent profile from SOUL.md: '{soul_data['name']}'")
            except (httpx.ConnectError, httpx.HTTPStatusError):
                pass  # Non-critical


def _bootstrap_clarke(
    endpoint: str, tenant_id: str, project_id: str, skip_superpowers: bool
) -> None:
    """Run the CLARKE bootstrap to create operator agent and ingest skills."""
    # Create operator agent
    try:
        resp = httpx.get(
            f"{endpoint}/agents/profiles",
            params={"tenant_id": tenant_id, "status": "active"},
            timeout=30.0,
        )
        resp.raise_for_status()
        existing = resp.json()
        has_operator = any(p.get("slug") == "clarke-operator" for p in existing)

        if not has_operator:
            from scripts.bootstrap_clarke_skills import CLARKE_OPERATOR

            resp = httpx.post(
                f"{endpoint}/agents/profiles",
                json={"tenant_id": tenant_id, "project_id": project_id, **CLARKE_OPERATOR},
                timeout=30.0,
            )
            resp.raise_for_status()
            print("  Created CLARKE Operator agent profile")
        else:
            print("  CLARKE Operator agent already exists")
    except Exception as e:
        print(f"  Agent bootstrap warning: {e}", file=sys.stderr)

    # Ingest skills into CLARKE's Qdrant
    skills_dir = PLUGIN_DIR / "skills"
    ingested = 0
    for skill_dir in sorted(skills_dir.iterdir()):
        if not skill_dir.is_dir():
            continue
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.exists():
            continue

        content = skill_file.read_text()
        # Strip frontmatter
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                content = parts[2].strip()

        try:
            resp = httpx.post(
                f"{endpoint}/agents/skills",
                json={
                    "tenant_id": tenant_id,
                    "project_id": project_id,
                    "skill_name": skill_dir.name,
                    "content": content,
                    "trigger_conditions": [],
                    "agent_capabilities": ["clarke-admin"],
                    "priority": 1,
                },
                timeout=60.0,
            )
            resp.raise_for_status()
            ingested += 1
        except (httpx.ConnectError, httpx.HTTPStatusError):
            pass  # Non-critical
    print(f"  Ingested {ingested} skills into CLARKE")

    # Superpowers (reuse bootstrap logic)
    if not skip_superpowers:
        try:
            from scripts.bootstrap_clarke_skills import (
                clone_superpowers,
                find_superpowers_agents,
                find_superpowers_skills,
                ingest_skill,
                superpowers_agent_to_profile,
                superpowers_skill_metadata,
                upsert_agent_profile,
            )

            print("  Cloning superpowers...")
            sp_dir = clone_superpowers()
            if sp_dir:
                for name, path in find_superpowers_agents(sp_dir):
                    from scripts.bootstrap_clarke_skills import parse_agent_file

                    fm, body = parse_agent_file(path)
                    profile = superpowers_agent_to_profile(name, fm, body)
                    upsert_agent_profile(endpoint, tenant_id, project_id, profile, dry_run=False)

                for name, path in find_superpowers_skills(sp_dir):
                    from scripts.bootstrap_clarke_skills import parse_skill_file

                    fm, content = parse_skill_file(path)
                    metadata = superpowers_skill_metadata(name, fm)
                    ingest_skill(
                        endpoint,
                        tenant_id,
                        project_id,
                        f"sp-{name}",
                        content,
                        metadata,
                        dry_run=False,
                    )

                import shutil as _shutil

                _shutil.rmtree(sp_dir, ignore_errors=True)
                print("  Superpowers skills ingested")
        except Exception as e:
            print(f"  Superpowers bootstrap warning: {e}", file=sys.stderr)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Install CLARKE memory engine into an OpenClaw workspace"
    )
    parser.add_argument(
        "--workspace", type=str, help="OpenClaw workspace path (default: auto-detect)"
    )
    parser.add_argument("--endpoint", default="http://localhost:8000", help="CLARKE API endpoint")
    parser.add_argument("--tenant-name", default="default", help="Tenant name")
    parser.add_argument("--project-name", default="default", help="Project name")
    parser.add_argument("--agent-slug", default="clarke-operator", help="Default agent slug")
    parser.add_argument(
        "--skip-backend", action="store_true", help="Skip docker/migration/server setup"
    )
    parser.add_argument("--skip-backup", action="store_true", help="Skip backing up existing files")
    parser.add_argument("--skip-superpowers", action="store_true", help="Skip superpowers clone")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done")
    args = parser.parse_args()

    install(args)


if __name__ == "__main__":
    main()
