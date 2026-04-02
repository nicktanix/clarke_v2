#!/usr/bin/env python3
"""One-shot CLARKE installer for OpenClaw.

Works for both fresh installs and reconfiguring existing ones.

Fresh install:
    python openclaw/install.py --workspace /path/to/openclaw/workspace

Reconfigure existing:
    python openclaw/install.py --workspace /path/to/openclaw/workspace --reconfigure

With CLARKE backend already running:
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
    """Run the full installation or reconfiguration."""
    reconfigure = args.reconfigure
    mode = "Reconfiguration" if reconfigure else "Installation"
    print(f"=== CLARKE for OpenClaw — {mode} ===\n")

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

    # Find the OpenClaw config root (parent of workspace/ if applicable)
    config_path = find_openclaw_config(workspace)
    openclaw_root = config_path.parent if config_path else workspace.parent
    print(f"  Config:    {config_path or 'not found'}")

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

    # ── 3. Create tenant + project (keyed to workspace path) ─────────
    # Each workspace gets its own CLARKE project. The tenant represents
    # the OpenClaw installation. This means multi-agent setups with
    # different workspaces get isolated CLARKE context automatically.
    project_name = args.project_name
    if project_name == "default":
        # Derive project name from workspace path for automatic isolation
        project_name = f"openclaw:{str(workspace).replace('/', ':')}"

    print("\n--- Tenant & Project ---")
    print(f"  Workspace key: {project_name}")
    if dry_run:
        print("  [dry-run] Would create tenant/project")
        tenant_id = "dry-run-tenant-id"
        project_id = "dry-run-project-id"
    else:
        try:
            tenant_id, project_id = ensure_tenant_project(endpoint, args.tenant_name, project_name)
            print(f"  Tenant:  {tenant_id}")
            print(f"  Project: {project_id}")
        except (httpx.ConnectError, httpx.HTTPStatusError) as e:
            print(f"  Failed to create tenant/project: {e}", file=sys.stderr)
            sys.exit(1)

    # ── 4. Discover + backup existing content ───────────────────────
    if not reconfigure:
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
            existing = {}
            print("  No existing agent files found")

        # ── 5. Ingest existing content into CLARKE ──────────────────
        if not dry_run and not args.skip_backend and existing:
            print("\n--- Ingesting Existing Content ---")
            _ingest_existing_content(workspace, existing, endpoint, tenant_id, project_id)
    else:
        print("\n--- Skipping backup/ingestion (reconfigure mode) ---")

    # ── 6. Register MCP server in openclaw.json ─────────────────────
    print("\n--- MCP Registration ---")
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

    # ── 7. Register plugin in openclaw.json ─────────────────────────
    print("\n--- Plugin Registration ---")
    if config_path:
        if dry_run:
            print(f"  [dry-run] Would register CLARKE plugin in {config_path}")
        else:
            config = read_config(config_path)
            _register_plugin(config, config_path)
            print(f"  Registered CLARKE plugin in {config_path}")
    else:
        print("  openclaw.json not found — skipping plugin registration")

    # ── 8. Write CLARKE env vars ────────────────────────────────────
    print("\n--- Environment Configuration ---")
    _write_env_config(
        openclaw_root, workspace, endpoint, tenant_id, project_id, args.agent_slug, dry_run
    )

    # ── 9. Install skills ───────────────────────────────────────────
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

    # ── 10. Build TypeScript plugin ─────────────────────────────────
    print("\n--- Building Plugin ---")
    if dry_run:
        print("  [dry-run] Would run npm install && npm run build")
    else:
        _build_plugin()

    # ── 11. Bootstrap CLARKE (agents + skills into Qdrant) ──────────
    if not dry_run and not args.skip_backend:
        print("\n--- CLARKE Bootstrap ---")
        _bootstrap_clarke(endpoint, tenant_id, project_id, args.skip_superpowers)

    # ── Report ──────────────────────────────────────────────────────
    print("\n" + "=" * 50)
    print(f"CLARKE {mode.lower()} complete!")
    print(f"  Workspace:    {workspace}")
    print(f"  Endpoint:     {endpoint}")
    print(f"  Tenant:       {tenant_id}")
    print(f"  Project:      {project_id}")
    print(f"  Agent:        {args.agent_slug}")
    print(f"  Skills:       {installed_skills}")
    print(f"  Plugin:       {PLUGIN_DIR / 'dist' / 'index.js'}")
    print()
    print("How it works:")
    print("  - before_prompt_build: CLARKE context injected into every system prompt")
    print("  - before_agent_reply:  User queries augmented with retrieval context")
    print("  - llm_output:          Interactions fed back for learning")
    print()
    print("Commands:")
    print("  /clarke          — system dashboard")
    print("  /clarke-teach    — record decisions and corrections")
    print("  /clarke-recall   — query CLARKE's memory")
    print("  /clarke-review   — approve self-improvement proposals")


def _register_plugin(config: dict, config_path: Path) -> None:
    """Register the CLARKE plugin in openclaw.json.

    OpenClaw discovers plugins from paths listed in plugins.load.paths[].
    Each path must contain a openclaw.plugin.json manifest. Plugin-specific
    config goes under plugins.entries.<name>.config.
    """
    plugins = config.setdefault("plugins", {})

    # Remove any stale "native" key from previous installs
    plugins.pop("native", None)

    plugins["enabled"] = True

    # Add CLARKE plugin parent to load paths.
    # OpenClaw scans load paths for subdirectories containing openclaw.plugin.json.
    # So we add the parent of the plugin dir (e.g., ~/.clarke) and OpenClaw finds
    # ~/.clarke/openclaw/openclaw.plugin.json.
    load = plugins.setdefault("load", {})
    paths = load.setdefault("paths", [])
    plugin_parent = str(PLUGIN_DIR.parent)
    # Clean up stale entries pointing to the plugin dir itself
    paths[:] = [p for p in paths if p != str(PLUGIN_DIR)]
    if plugin_parent not in paths:
        paths.append(plugin_parent)

    # Remove stale entries — plugin is discovered from load path, no entry needed
    entries = plugins.get("entries", {})
    entries.pop("clarke", None)
    if entries:
        plugins["entries"] = entries
    elif "entries" in plugins:
        del plugins["entries"]

    write_config(config_path, config)


def _write_env_config(
    openclaw_root: Path,
    workspace: Path,
    endpoint: str,
    tenant_id: str,
    project_id: str,
    agent_slug: str,
    dry_run: bool,
) -> None:
    """Write CLARKE env vars to the OpenClaw .env file."""
    env_vars = {
        "CLARKE_API_URL": endpoint,
        "CLARKE_TENANT_ID": tenant_id,
        "CLARKE_PROJECT_ID": project_id,
        "CLARKE_AGENT_SLUG": agent_slug,
        "OPENCLAW_WORKSPACE": str(workspace),
    }

    env_file = openclaw_root / ".env"

    if dry_run:
        print("  [dry-run] Would write to .env:")
        for k, v in env_vars.items():
            print(f"    {k}={v}")
        return

    # Read existing .env if present
    existing_lines: list[str] = []
    existing_keys: set[str] = set()
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            key = line.split("=", 1)[0].strip()
            if key in env_vars:
                # Update existing CLARKE vars
                existing_lines.append(f"{key}={env_vars[key]}")
                existing_keys.add(key)
            else:
                existing_lines.append(line)

    # Ensure trailing newline before appending
    if existing_lines and existing_lines[-1] != "":
        existing_lines.append("")

    # Append any new CLARKE vars
    new_vars = {k: v for k, v in env_vars.items() if k not in existing_keys}
    if new_vars:
        existing_lines.append("# CLARKE Plugin Configuration")
        for k, v in new_vars.items():
            existing_lines.append(f"{k}={v}")

    env_file.write_text("\n".join(existing_lines) + "\n")

    for k, v in env_vars.items():
        status = "updated" if k in existing_keys else "added"
        print(f"  {status}: {k}={v}")


def _build_plugin() -> None:
    """Build the TypeScript plugin."""
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
        print("  Run: cd openclaw && npm install && npm run build", file=sys.stderr)
    except FileNotFoundError:
        print("  npm not found — skipping plugin build", file=sys.stderr)
        print("  Run: cd openclaw && npm install && npm run build", file=sys.stderr)


def _ingest_existing_content(
    workspace: Path,
    existing: dict[str, Path],
    endpoint: str,
    tenant_id: str,
    project_id: str,
) -> None:
    """Ingest existing SOUL.md/AGENTS.md content into CLARKE."""
    for name in ("SOUL.md", "AGENTS.md", "TOOLS.md", "USER.md", "IDENTITY.md"):
        if name not in existing:
            continue
        path = existing[name]
        content = path.read_text()
        if not content.strip():
            continue

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
                pass


def _bootstrap_clarke(
    endpoint: str, tenant_id: str, project_id: str, skip_superpowers: bool
) -> None:
    """Run the CLARKE bootstrap to create operator agent and ingest skills."""
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

    # Ingest skills
    skills_dir = PLUGIN_DIR / "skills"
    ingested = 0
    for skill_dir in sorted(skills_dir.iterdir()):
        if not skill_dir.is_dir():
            continue
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.exists():
            continue
        content = skill_file.read_text()
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
            pass
    print(f"  Ingested {ingested} skills into CLARKE")

    if not skip_superpowers:
        try:
            from scripts.bootstrap_clarke_skills import (
                clone_superpowers,
                find_superpowers_agents,
                find_superpowers_skills,
                ingest_skill,
                parse_agent_file,
                parse_skill_file,
                superpowers_agent_to_profile,
                superpowers_skill_metadata,
                upsert_agent_profile,
            )

            print("  Cloning superpowers...")
            sp_dir = clone_superpowers()
            if sp_dir:
                for name, path in find_superpowers_agents(sp_dir):
                    fm, body = parse_agent_file(path)
                    profile = superpowers_agent_to_profile(name, fm, body)
                    upsert_agent_profile(endpoint, tenant_id, project_id, profile, dry_run=False)

                for name, path in find_superpowers_skills(sp_dir):
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

                shutil.rmtree(sp_dir, ignore_errors=True)
                print("  Superpowers skills ingested")
        except Exception as e:
            print(f"  Superpowers bootstrap warning: {e}", file=sys.stderr)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Install or reconfigure CLARKE for an OpenClaw workspace"
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
    parser.add_argument(
        "--reconfigure",
        action="store_true",
        help="Reconfigure existing install (skip backup/ingestion, update config + plugin + skills)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done")
    args = parser.parse_args()

    install(args)


if __name__ == "__main__":
    main()
