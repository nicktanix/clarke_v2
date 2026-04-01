# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

CLARKE (Cognitive Learning Augmentation Retrieval Knowledge Engine) is a brokered context and memory system for LLM applications. It sits between an application and one or more LLMs to deliver the smallest sufficient grounded context before a model call, support structured escalation (CONTEXT_REQUEST, SUBAGENT_SPAWN), and improve retrieval over time through learned weights and emergent classification. Python 3.12+, currently under active implementation.

## Tech Stack (Decided)

- **FastAPI** — Broker API
- **LangGraph** — Execution graph / orchestration
- **PostgreSQL** — Canonical store, audit, metadata (SQLAlchemy 2.0 async + Alembic)
- **Qdrant** — Semantic + hybrid retrieval
- **Neo4j** — Graph memory, convergence anchors (post-MVP)
- **LiteLLM** — Unified model gateway
- **Sentence Transformers** — Cross-encoder reranking
- **Unstructured** — Document parsing
- **OpenTelemetry** — Tracing
- **Phoenix** — LLM eval
- **Temporal** — Background jobs (post-MVP)
- **Pydantic** — Schemas and settings
- **structlog** — Structured logging
- **ULIDs** — All IDs, prefixed by entity type (`r_`, `ep_`, `tr_`)

## Development Commands

```bash
make install       # pip install -e ".[dev]" + pre-commit install
make dev           # docker compose up + alembic upgrade head + uvicorn --reload
make migrate       # alembic upgrade head
make migration     # alembic revision --autogenerate -m "description"
make test          # pytest tests/
make lint          # ruff check + ruff format --check
make typecheck     # mypy clarke/
make fmt           # ruff format + ruff check --fix
make clean         # stop docker, remove volumes
```

Run a single test: `pytest tests/api/test_query.py::test_name -v`

## Architecture

```
User / Parent-Agent Request
  → FastAPI Broker API (clarke/api/)
    → LangGraph Execution Graph (clarke/graph/)
      → Retrieval Layer (clarke/retrieval/) — Qdrant, Neo4j
      → Context Composer (clarke/retrieval/composer/)
      → LLM Gateway (clarke/llm/) — LiteLLM
      → Optional CONTEXT_REQUEST loop
      → Optional SUBAGENT_SPAWN
    → Persistence (clarke/storage/postgres/)
    → Telemetry (clarke/telemetry/)
```

### Key directories

- `clarke/api/` — FastAPI app, routes, schemas, middleware, dependency injection
- `clarke/broker/` — Broker service, contracts, policy, budget, degraded mode logic
- `clarke/graph/` — LangGraph workflow, state definition, individual node functions
- `clarke/graph/nodes/` — One file per graph node; nodes must be thin and delegate to domain services
- `clarke/retrieval/` — Planner, Qdrant client, Neo4j client, reranker, context composer
- `clarke/llm/` — LiteLLM gateway, prompts, token counting, response contracts
- `clarke/storage/postgres/` — SQLAlchemy models, repository pattern, database connection
- `clarke/ingestion/` — Document parsing, chunking, redaction, embeddings
- `clarke/learning/` — Attribution, usefulness scoring, weight updates, clustering
- `clarke/agents/` — Sub-agent runtime, spawn, lifecycle, result handling
- `clarke/memory/` — Memory models, episodic/semantic/decision/policy layers
- `clarke/telemetry/` — OpenTelemetry tracing, structlog logging, metrics

### Graph node pattern

Each LangGraph node is an async function in `clarke/graph/nodes/` that takes `BrokerState` (a flat TypedDict) and returns a partial state update dict. Business logic lives in the broker, LLM, and storage layers — nodes only orchestrate.

## Design Principles (Non-Negotiable)

1. **Broker-owned retrieval** — Models never directly access storage. They request context through structured contracts only.
2. **Smallest sufficient context** — Optimize for useful context per token, not maximum recall.
3. **Explicit trust ordering** — When conflicts appear: canonical policy > structured decisions > authoritative docs > episodic summaries > semantic neighbors. Surface conflicts explicitly.
4. **Tenant isolation everywhere** — Every retrieval and persistence path enforces `tenant_id`, `project_id`, `user_id`. Qdrant payload filters, Neo4j query predicates, PostgreSQL RLS.
5. **Safe degradation** — When dependencies fail, fall back to reduced or canonical-only mode. Never fail open. Propagate `degraded_mode` through state and telemetry.
6. **Classes must be earned** — No predefined taxonomy. Proto-classes emerge from retrieval behavior and must meet stability/member thresholds before influencing routing.
7. **Prompts are code** — Constitutional prompts and context templates are versioned, tracked by ID on every request.

## Key Contracts

Three structured model output types are treated as stable internal protocol:

- **`CONTEXT_REQUEST`** — Model requests additional context via structured JSON. Broker validates source, quota, budget.
- **`SUBAGENT_SPAWN`** — Model requests creation of a bounded runtime sub-agent. Broker validates separability, depth, budget, tenant scope.
- **`SUBAGENT_RESULT`** — Child agent returns structured results. Parent must explicitly consume or ignore.

## Development Phases

1. **Foundation + Functional Broker** — FastAPI, LangGraph, LiteLLM, PostgreSQL, OTel scaffolding
2. **Document Ingestion + Semantic Retrieval** — Unstructured, Qdrant, reranking, exact token counting
3. **Learning Loop** — CONTEXT_REQUEST loop, attribution, Phoenix, weight tuning, exploration
4. **Graph Memory** — Neo4j, convergence anchors, decision/policy memory, trust precedence
5. **Emergent Taxonomy** — HDBSCAN clustering, proto-classes, route improvement
6. **Multi-Agent Support** — SUBAGENT_SPAWN lifecycle, inherited context, lineage

## Spec Documents

- `docs/clarke.md` — Expanded reference architecture (canonical detailed spec)
- `docs/draft/brokered-context-memory-system-v3.1.md` — Unified spec v3.1
- `docs/draft/brokered-context-memory-system-milestones-v2.md` — Milestone breakdown

<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **clarke_v2** (2461 symbols, 4892 relationships, 123 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

> If any GitNexus tool warns the index is stale, run `npx gitnexus analyze` in terminal first.

## Always Do

- **MUST run impact analysis before editing any symbol.** Before modifying a function, class, or method, run `gitnexus_impact({target: "symbolName", direction: "upstream"})` and report the blast radius (direct callers, affected processes, risk level) to the user.
- **MUST run `gitnexus_detect_changes()` before committing** to verify your changes only affect expected symbols and execution flows.
- **MUST warn the user** if impact analysis returns HIGH or CRITICAL risk before proceeding with edits.
- When exploring unfamiliar code, use `gitnexus_query({query: "concept"})` to find execution flows instead of grepping. It returns process-grouped results ranked by relevance.
- When you need full context on a specific symbol — callers, callees, which execution flows it participates in — use `gitnexus_context({name: "symbolName"})`.

## When Debugging

1. `gitnexus_query({query: "<error or symptom>"})` — find execution flows related to the issue
2. `gitnexus_context({name: "<suspect function>"})` — see all callers, callees, and process participation
3. `READ gitnexus://repo/clarke_v2/process/{processName}` — trace the full execution flow step by step
4. For regressions: `gitnexus_detect_changes({scope: "compare", base_ref: "main"})` — see what your branch changed

## When Refactoring

- **Renaming**: MUST use `gitnexus_rename({symbol_name: "old", new_name: "new", dry_run: true})` first. Review the preview — graph edits are safe, text_search edits need manual review. Then run with `dry_run: false`.
- **Extracting/Splitting**: MUST run `gitnexus_context({name: "target"})` to see all incoming/outgoing refs, then `gitnexus_impact({target: "target", direction: "upstream"})` to find all external callers before moving code.
- After any refactor: run `gitnexus_detect_changes({scope: "all"})` to verify only expected files changed.

## Never Do

- NEVER edit a function, class, or method without first running `gitnexus_impact` on it.
- NEVER ignore HIGH or CRITICAL risk warnings from impact analysis.
- NEVER rename symbols with find-and-replace — use `gitnexus_rename` which understands the call graph.
- NEVER commit changes without running `gitnexus_detect_changes()` to check affected scope.

## Tools Quick Reference

| Tool | When to use | Command |
|------|-------------|---------|
| `query` | Find code by concept | `gitnexus_query({query: "auth validation"})` |
| `context` | 360-degree view of one symbol | `gitnexus_context({name: "validateUser"})` |
| `impact` | Blast radius before editing | `gitnexus_impact({target: "X", direction: "upstream"})` |
| `detect_changes` | Pre-commit scope check | `gitnexus_detect_changes({scope: "staged"})` |
| `rename` | Safe multi-file rename | `gitnexus_rename({symbol_name: "old", new_name: "new", dry_run: true})` |
| `cypher` | Custom graph queries | `gitnexus_cypher({query: "MATCH ..."})` |

## Impact Risk Levels

| Depth | Meaning | Action |
|-------|---------|--------|
| d=1 | WILL BREAK — direct callers/importers | MUST update these |
| d=2 | LIKELY AFFECTED — indirect deps | Should test |
| d=3 | MAY NEED TESTING — transitive | Test if critical path |

## Resources

| Resource | Use for |
|----------|---------|
| `gitnexus://repo/clarke_v2/context` | Codebase overview, check index freshness |
| `gitnexus://repo/clarke_v2/clusters` | All functional areas |
| `gitnexus://repo/clarke_v2/processes` | All execution flows |
| `gitnexus://repo/clarke_v2/process/{name}` | Step-by-step execution trace |

## Self-Check Before Finishing

Before completing any code modification task, verify:
1. `gitnexus_impact` was run for all modified symbols
2. No HIGH/CRITICAL risk warnings were ignored
3. `gitnexus_detect_changes()` confirms changes match expected scope
4. All d=1 (WILL BREAK) dependents were updated

## Keeping the Index Fresh

After committing code changes, the GitNexus index becomes stale. Re-run analyze to update it:

```bash
npx gitnexus analyze
```

If the index previously included embeddings, preserve them by adding `--embeddings`:

```bash
npx gitnexus analyze --embeddings
```

To check whether embeddings exist, inspect `.gitnexus/meta.json` — the `stats.embeddings` field shows the count (0 means no embeddings). **Running analyze without `--embeddings` will delete any previously generated embeddings.**

> Claude Code users: A PostToolUse hook handles this automatically after `git commit` and `git merge`.

## CLI

| Task | Read this skill file |
|------|---------------------|
| Understand architecture / "How does X work?" | `.claude/skills/gitnexus/gitnexus-exploring/SKILL.md` |
| Blast radius / "What breaks if I change X?" | `.claude/skills/gitnexus/gitnexus-impact-analysis/SKILL.md` |
| Trace bugs / "Why is X failing?" | `.claude/skills/gitnexus/gitnexus-debugging/SKILL.md` |
| Rename / extract / split / refactor | `.claude/skills/gitnexus/gitnexus-refactoring/SKILL.md` |
| Tools, resources, schema reference | `.claude/skills/gitnexus/gitnexus-guide/SKILL.md` |
| Index, status, clean, wiki CLI commands | `.claude/skills/gitnexus/gitnexus-cli/SKILL.md` |

<!-- gitnexus:end -->
