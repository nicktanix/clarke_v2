# CLARKE — Architecture & Internals

This document covers CLARKE's architecture, design principles, tech stack, and contributor guidance. For getting started and integration guides, see the [project README](../README.md).

---

## What CLARKE Does

CLARKE sits between an application and one or more LLMs. It:

- classifies retrieval intent from weak signals rather than hard-coded ontologies
- retrieves relevant evidence from memory, docs, decisions, and policy
- builds a compact context pack within exact token budgets
- calls the model with broker-governed context
- supports structured `CONTEXT_REQUEST` escalation
- supports bounded `SUBAGENT_SPAWN` for separable sub-tasks
- logs provenance, usefulness, and context waste
- improves routing and retrieval over time

At a high level, CLARKE is a **memory broker**, **retrieval planner**, **context composer**, **policy boundary**, and **learning loop** in one system.

---

## Core Principles

These are non-negotiable:

- **Broker-owned retrieval** — Models do not directly browse memory or storage. They request context through structured contracts only.
- **Smallest sufficient context** — Optimize for useful context per token, not maximum recall.
- **Explicit trust ordering** — Policy > decisions > docs > episodic > semantic. Surface conflicts explicitly.
- **Classes must be earned** — No predefined taxonomy. Proto-classes emerge from retrieval behavior and must meet stability/member thresholds.
- **Safe degradation** — Fall back to reduced or canonical-only modes. Never fail open.
- **Tenant-safe by default** — Every retrieval and persistence path enforces tenant_id, project_id, user_id.
- **Prompts are code** — Constitutional prompts and context templates are versioned and tracked by ID.

---

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

### Key Directories

| Directory | Purpose |
|-----------|---------|
| `clarke/api/` | FastAPI app, routes, schemas, middleware, dependency injection |
| `clarke/broker/` | Broker service, contracts, policy, budget, degraded mode |
| `clarke/graph/` | LangGraph workflow, state definition, node functions |
| `clarke/retrieval/` | Planner, Qdrant client, Neo4j client, reranker, context composer |
| `clarke/llm/` | LiteLLM gateway, prompts, token counting, response contracts |
| `clarke/storage/postgres/` | SQLAlchemy models, repository pattern, database connection |
| `clarke/ingestion/` | Document parsing, chunking, redaction, embeddings |
| `clarke/learning/` | Attribution, usefulness scoring, weight updates, clustering, self-improvement |
| `clarke/agents/` | Sub-agent runtime, spawn, lifecycle, session context builder |
| `clarke/memory/` | Memory models, episodic/semantic/decision/policy layers |
| `clarke/mcp/` | MCP server with 15 tools for Claude Code / OpenClaw integration |
| `clarke/telemetry/` | OpenTelemetry tracing, structlog logging, metrics |

### Graph Node Pattern

Each LangGraph node is an async function in `clarke/graph/nodes/` that takes `BrokerState` (a flat TypedDict) and returns a partial state update dict. Business logic lives in the broker, LLM, and storage layers — nodes only orchestrate.

---

## Tech Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| API | FastAPI | Broker API, typed contracts |
| Orchestration | LangGraph | Execution graph, bounded loops |
| Database | PostgreSQL | Canonical store, audit, metadata |
| Retrieval | Qdrant | Semantic + hybrid search |
| Graph | Neo4j | Graph memory, convergence anchors |
| LLM Gateway | LiteLLM | Unified model access |
| Reranking | Sentence Transformers | Cross-encoder reranking |
| Ingestion | Unstructured | Document parsing |
| Tracing | OpenTelemetry | Distributed tracing |
| Evaluation | Phoenix | LLM eval, replay experiments |
| Background Jobs | Temporal | Durable execution (post-MVP) |
| Schemas | Pydantic | Request/response validation |
| Logging | structlog | Structured JSON logging |
| IDs | ULIDs | Prefixed by entity type (r\_, ep\_, tr\_) |

---

## Model Contracts

Three structured model output types are treated as stable internal protocol:

- **`CONTEXT_REQUEST`** — Model requests additional context via structured JSON. Broker validates source, quota, budget.
- **`SUBAGENT_SPAWN`** — Model requests creation of a bounded runtime sub-agent. Broker validates separability, depth, budget, tenant scope.
- **`SUBAGENT_RESULT`** — Child agent returns structured results. Parent must explicitly consume or ignore.

---

## Development Phases

1. **Foundation + Functional Broker** — FastAPI, LangGraph, LiteLLM, PostgreSQL, OTel scaffolding
2. **Document Ingestion + Semantic Retrieval** — Unstructured, Qdrant, reranking, exact token counting
3. **Learning Loop** — CONTEXT_REQUEST loop, attribution, Phoenix, weight tuning, exploration
4. **Graph Memory** — Neo4j, convergence anchors, decision/policy memory, trust precedence
5. **Emergent Taxonomy** — HDBSCAN clustering, proto-classes, route improvement
6. **Multi-Agent Support** — SUBAGENT_SPAWN lifecycle, inherited context, lineage
7. **Dynamic Agent Context** — Agent profiles, session context builder, skill effectiveness, directive surfacing

---

## Retrieval Philosophy

CLARKE is not "just RAG." It is:

- retrieval planning with learned source weights
- trust-aware composition with conflict detection
- exact token budgeting per section
- provenance-preserving context assembly
- post-answer attribution
- outcome-driven improvement via feedback loops

The retrieval system optimizes for **useful context per token**, not raw recall or similarity.

---

## Data and Security

### Required Guarantees

- Tenant isolation across all stores (PostgreSQL RLS, Qdrant payload filters, Neo4j query predicates)
- Audit logging for memory writes and policy changes
- Redacted retrieval indexes (PII scrubbed before embedding)
- Policy approval workflow before canonical activation

### Trust Rule

A parent agent can request memory for a sub-agent, but **the broker is the only authority that can approve and assemble that memory**.

---

## Environment Variables

Key settings (all prefixed with `CLARKE_`):

```env
CLARKE_ENV=development
CLARKE_POSTGRES_URL=postgresql+asyncpg://clarke:clarke_dev@localhost:5432/clarke
CLARKE_DEFAULT_ANSWER_MODEL=gpt-4o-mini
CLARKE_QDRANT_HOST=localhost
CLARKE_QDRANT_PORT=6333
CLARKE_EMBEDDING_MODEL=text-embedding-3-small
CLARKE_NEO4J_URI=bolt://localhost:7687
CLARKE_GRAPH_ENABLED=true
CLARKE_SESSION_CONTEXT_ENABLED=false
CLARKE_SELF_IMPROVEMENT_ENABLED=false
CLARKE_OTEL_ENABLED=false
```

See `clarke/settings.py` for the complete settings reference with defaults.

---

## Metrics

CLARKE tracks:

- Request latency and degraded mode rate
- Useful context ratio (attributed tokens / injected tokens)
- Source usefulness by type and strategy
- Retrieval plan usefulness
- Proto-class stability over time
- Skill effectiveness scores
- Directive proposal acceptance rate

---

## Contribution Guidance

When contributing:

- Keep broker contracts explicit
- Do not let models directly read storage
- Preserve tenant isolation in every layer
- Prefer deterministic broker behavior over hidden magic
- Optimize for smallest sufficient context
- Log provenance for anything injected into a prompt
- Treat prompt changes like code changes
- Do not add agent coordination primitives casually

---

## Spec Documents

- `docs/clarke.md` — Expanded reference architecture (canonical detailed spec)
- `docs/draft/brokered-context-memory-system-v3.1.md` — Unified spec v3.1
- `docs/draft/brokered-context-memory-system-milestones-v2.md` — Milestone breakdown
