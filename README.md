# CLARKE

**Cognitive Learning Augmentation Retrieval Knowledge Engine**

CLARKE gives your AI agents persistent memory, learned context, and self-improving skills. It replaces static configuration files with a dynamic context engine that gets smarter with every interaction.

---

## What You Get

- **Persistent memory** — decisions, policies, corrections, and domain knowledge survive across sessions
- **Dynamic context** — agents get the right context for each interaction, not a giant static prompt
- **Self-improvement** — CLARKE learns which skills work, surfaces behavioral improvements, and adapts over time
- **Multi-agent support** — shared memory and policies across agent teams with tenant isolation
- **Works with your tools** — first-party integrations for Claude Code and OpenClaw

---

## Quick Start

### Prerequisites

- Python 3.12+
- Docker and Docker Compose
- An OpenAI API key (for embeddings) or compatible provider

### 1. Install

```bash
git clone https://github.com/clarke-ai/clarke.git
cd clarke
make install
```

### 2. Start the Backend

```bash
make dev
```

This starts PostgreSQL, Qdrant, and Neo4j via Docker Compose, runs database migrations, and launches the CLARKE API server at `http://localhost:8000`.

### 3. Bootstrap Skills

```bash
python scripts/bootstrap_clarke_skills.py \
    --tenant-id <your-tenant-uuid> \
    --project-id <your-project-uuid>
```

This seeds CLARKE with agent profiles and 22 skills (8 CLARKE management + 14 development workflow skills from [superpowers](https://github.com/obra/superpowers)). It also configures MCP tools and hooks in your global Claude Code settings.

Use `--dry-run` to preview what will be created.

### 4. Verify

```bash
curl http://localhost:8000/health
```

---

## Integrations

### Claude Code

CLARKE integrates with Claude Code through MCP tools, slash commands, and session hooks.

**Setup:**

The bootstrap script (step 3 above) automatically configures:
- **MCP server** in `~/.claude/.mcp.json` — 15 tools for querying, teaching, managing agents
- **Session hook** in `~/.claude/settings.json` — injects CLARKE context at session start
- **AGENTS.md** — minimal stub with CLARKE connection metadata

**Available slash commands after bootstrap:**

| Command | Purpose |
|---------|---------|
| `/clarke` | Dashboard — system health, active agents, policies |
| `/clarke-agent` | Create, list, update, or archive agent profiles |
| `/clarke-skill` | Author and ingest new skills |
| `/clarke-teach` | Record decisions, policies, corrections |
| `/clarke-recall` | Query CLARKE's memory with source attribution |
| `/clarke-review` | Approve or reject self-improvement proposals |
| `/clarke-ingest` | Feed documents and files into CLARKE |
| `/clarke-configure` | View and modify settings |

**Manual MCP setup** (if not using the bootstrap script):

```json
{
  "mcpServers": {
    "clarke": {
      "command": "python",
      "args": ["-m", "clarke.mcp.server"],
      "env": { "CLARKE_API_URL": "http://localhost:8000" }
    }
  }
}
```

### OpenClaw

CLARKE provides a one-shot installer for [OpenClaw](https://github.com/openclaw/openclaw) workspaces.

**Install into an OpenClaw workspace:**

```bash
python openclaw/install.py --workspace /path/to/openclaw/workspace
```

This single command:
1. Starts the CLARKE backend (Docker services + migrations + API)
2. Creates a tenant and project for this workspace
3. Backs up existing `SOUL.md` and `AGENTS.md` to `.clarke-backup/`
4. Ingests existing agent content into CLARKE's memory
5. Registers CLARKE's MCP server in `openclaw.json`
6. Installs skills and a context-refresh hook
7. Writes CLARKE context into workspace files

**How it works:** OpenClaw's Brain reads `SOUL.md` on every LLM call. CLARKE writes dynamic context between `<!-- clarke:start -->` / `<!-- clarke:end -->` markers. User content outside the markers is preserved.

**If CLARKE is already running:**

```bash
python openclaw/install.py \
    --workspace /path/to/workspace \
    --endpoint http://your-clarke-host:8000 \
    --skip-backend
```

**Options:**

| Flag | Effect |
|------|--------|
| `--workspace PATH` | OpenClaw workspace (default: auto-detect) |
| `--endpoint URL` | CLARKE API endpoint (default: `http://localhost:8000`) |
| `--skip-backend` | Skip Docker/migration setup |
| `--skip-superpowers` | Skip cloning superpowers skills |
| `--dry-run` | Preview without making changes |

---

## Features

### Dynamic Agent Context

Enable dynamic session context to replace static AGENTS.md files:

```bash
# In your .env file
CLARKE_SESSION_CONTEXT_ENABLED=true
```

Agents get their full context — directives, skills, policies, domain knowledge — composed dynamically at session start from CLARKE's memory layers.

### Self-Improvement

CLARKE learns from every interaction:

```bash
# In your .env file
CLARKE_SELF_IMPROVEMENT_ENABLED=true
```

- **Skill effectiveness** — tracks which skills lead to good outcomes, ranks them higher
- **Directive proposals** — when users keep correcting the same thing, CLARKE proposes a behavioral directive
- **Tenant-wide signals** — corrections that appear across multiple agents become policy candidates

Use `/clarke-review` to approve or reject proposals. The learning loop is propose-and-approve — CLARKE never changes agent behavior without human sign-off.

### Skills System

Skills are ingested into CLARKE and matched semantically at session build time. Priority levels control which skills get included when token budgets are tight.

**Author new skills** with `/clarke-skill` or ingest them via the API:

```bash
curl -X POST http://localhost:8000/agents/skills \
  -H 'Content-Type: application/json' \
  -d '{
    "tenant_id": "<uuid>",
    "project_id": "<uuid>",
    "skill_name": "deployment-checklist",
    "content": "## Steps\n1. Run tests\n2. Check staging\n3. Deploy",
    "trigger_conditions": ["deploy", "release", "ship"],
    "agent_capabilities": ["devops"],
    "priority": 1
  }'
```

### Memory Types

CLARKE maintains five memory layers with explicit trust ordering:

| Layer | Trust | Examples |
|-------|-------|---------|
| **Policy** | Highest | "All API endpoints must validate tenant_id" |
| **Decisions** | High | "We chose structlog because of structured JSON output" |
| **Documents** | Medium | Ingested docs, READMEs, specs |
| **Episodic** | Low | Past query/answer interactions |
| **Semantic** | Lowest | Vector similarity matches |

When sources conflict, higher-trust layers take precedence. Conflicts are surfaced explicitly.

### Degraded Mode

When dependencies fail, CLARKE falls back gracefully:

| Mode | Available | Missing |
|------|-----------|---------|
| **Full** | Everything | — |
| **Reduced** | Policies + decisions + docs | Graph retrieval |
| **Canonical only** | Policies + decisions | Semantic search, graph |

The agent always gets at least policy and decision context. Degraded mode is propagated through telemetry.

---

## Development

```bash
make install       # pip install -e ".[dev]" + pre-commit
make dev           # docker compose + migrations + uvicorn --reload
make test          # pytest tests/
make lint          # ruff check + format --check
make fmt           # ruff format + ruff check --fix
make typecheck     # mypy clarke/
make clean         # stop docker, remove volumes
```

Run a single test: `pytest tests/api/test_query.py::test_name -v`

### Migrate Existing Agent Files

If you have existing AGENTS.md or skill files:

```bash
python scripts/migrate_md_to_clarke.py \
    --agents-md AGENTS.md \
    --skills-dir .claude/skills/ \
    --tenant-id <uuid> \
    --project-id <uuid>
```

---

## API

CLARKE exposes a REST API at `http://localhost:8000`:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | System health |
| `/query` | POST | Send a query through the broker |
| `/feedback` | POST | Submit feedback on a query |
| `/ingest` | POST | Ingest a document |
| `/policy` | POST/GET | Create or list policies |
| `/decisions` | POST/GET | Record or list decisions |
| `/agents/profiles` | CRUD | Agent profile management |
| `/agents/session-context` | POST | Build dynamic session context |
| `/agents/skills` | POST | Ingest a skill |
| `/agents/profiles/{id}/directives/proposals` | GET/POST | Directive review queue |
| `/admin/setup` | POST | Create tenant + project |

Full API documentation is available at `http://localhost:8000/docs` when the server is running.

---

## Architecture & Internals

For detailed architecture documentation, design principles, tech stack decisions, and contributor guidance, see [clarke/README.md](clarke/README.md).

---

## License

Polyform Noncommercial 1.0.0 — free for personal, research, and noncommercial use.

For commercial and enterprise licensing, contact [nick@neill.cloud](mailto:nick@neill.cloud).
