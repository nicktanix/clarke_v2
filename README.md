# CLARKE
## Cognitive Learning Augmentation Retrieval Knowledge Engine

CLARKE is a **brokered context and memory system** for LLM applications.

Its job is to deliver the **smallest sufficient grounded context** before a model call, allow the model to request additional context through structured broker-mediated contracts, and improve over time by learning which retrieval plans actually help.

CLARKE is designed to replace large, stale runtime instruction files and ad hoc memory layers with a **tenant-safe, retrieval-aware, policy-governed context engine**.

---

## What CLARKE Does

CLARKE sits between an application and one or more LLMs. It:

- interprets a user request
- classifies retrieval intent from weak signals rather than hard-coded ontologies
- retrieves relevant evidence from memory, docs, decisions, and policy
- builds a compact context pack
- calls the model with broker-governed context
- supports structured `CONTEXT_REQUEST` escalation
- supports bounded broker-created `SUBAGENT_SPAWN` for separable sub-tasks
- logs provenance, usefulness, and context waste
- improves routing and retrieval over time

At a high level, CLARKE is a **memory broker**, **retrieval planner**, **context composer**, **policy boundary**, and **learning loop** in one system.

---

## Core Principles

CLARKE is built around a few non-negotiable design rules:

- **Broker-owned retrieval**  
  Models do not directly browse memory or storage. They can only request additional context through structured contracts.

- **Smallest sufficient context**  
  The goal is not maximum recall. The goal is the smallest context pack that is sufficient to answer well.

- **Leaves first, anchors second**  
  Initial retrieval should find relevant leaf evidence first, then identify convergence anchors or shared concepts.

- **Explicit trust ordering**  
  Canonical policy, structured decisions, authoritative docs, episodic memory, and semantic neighbors are not equivalent. CLARKE preserves source precedence.

- **Classes must be earned**  
  CLARKE does not depend on a perfect taxonomy on day one. It learns useful proto-classes from retrieval behavior and outcomes.

- **Safe degradation**  
  When dependencies fail, CLARKE falls back to reduced or canonical-only modes rather than failing open.

- **Tenant-safe by default**  
  All retrieval, storage, lineage, and learning paths are tenant-aware and policy-scoped.

---

## Primary Use Cases

CLARKE is a strong fit for:

- long-term memory for assistants
- project and workspace memory systems
- design-doc and decision retrieval
- retrieval-aware copilots
- policy-governed enterprise assistants
- hierarchical agent systems with bounded sub-agent support
- adaptive RAG / GraphRAG systems
- applications replacing static `AGENTS.md`, `MEMORY.md`, or similar runtime files

---

## High-Level Architecture

```text
User / Parent-Agent Request
   |
   v
FastAPI Broker API
   |
   v
LangGraph Execution Graph
   |
   +--> Query Understanding
   +--> Retrieval Planner
   +--> Semantic + Hybrid Retrieval (Qdrant)
   +--> Graph Retrieval (Neo4j / GraphRAG)
   +--> Canonical Metadata + Policy (PostgreSQL)
   +--> Context Composer / Budgeter
   +--> LiteLLM Gateway
   +--> Optional CONTEXT_REQUEST
   +--> Optional SUBAGENT_SPAWN
   +--> Attribution / Feedback / Learning
   |
   +--> OpenTelemetry + Phoenix + Temporal
```

---

## Tooling and Technology Selection

The current reference stack for CLARKE follows the design spec.

### Core API and orchestration
- **FastAPI**  
  Main broker API, typed request/response contracts, auth integration, streaming support.
- **LangGraph**  
  Execution graph, checkpointing, bounded loops, deterministic routing, and broker-controlled online flow.

### System of record and metadata
- **PostgreSQL**  
  Canonical metadata store for users, sessions, retrieval episodes, policy nodes, prompt versions, proto-classes, agent lineage, and audit logs.

### Retrieval
- **Qdrant**  
  Semantic and hybrid retrieval over redacted chunks, summaries, facts, decisions, and episodic memory.
- **Neo4j**  
  Graph memory, convergence anchors, decision lineage, relationship-aware retrieval, and runtime agent lineage.
- **Neo4j GraphRAG**  
  Graph-aware retrieval utilities and graph-based candidate generation.
- **Sentence Transformers Cross-Encoders**  
  Candidate reranking before context composition.

### Ingestion and preprocessing
- **Unstructured**  
  Document parsing and normalization.
- **Custom redaction / scrubbing layer**  
  Required before indexing into retrieval systems.

### Model access
- **LiteLLM**  
  Unified gateway across model providers, structured output support, retries, usage logging, and tokenizer-aware counting.
- **vLLM** *(optional / later)*  
  Self-hosted inference for local routing, evaluation, or lower-cost internal models.

### Background jobs and long-running workflows
- **Temporal** *(recommended after MVP)*  
  Durable execution for ingestion, clustering, replay evals, stale-edge pruning, and runtime-agent cleanup.

### Observability and evaluation
- **OpenTelemetry**  
  Tracing and metrics across the full broker path.
- **Phoenix**  
  LLM retrieval/response evaluation, replay experiments, groundedness checks, and usefulness measurement.

### Supporting implementation stack
- **Python 3.12+**
- **Pydantic**
- **SQLAlchemy or Piccolo** *(team choice; pick one and stay consistent)*
- **Alembic or native migration system**
- **Docker / Docker Compose**
- **pytest**
- **ruff**
- **mypy**
- **pre-commit**

---

## Why This Tool Selection

These choices are deliberate.

- **FastAPI + LangGraph** gives a strong Python control plane with explicit flow control.
- **PostgreSQL** is the canonical truth store and audit layer.
- **Qdrant** handles fast semantic recall and hybrid search.
- **Neo4j** handles structure, lineage, convergence, and graph-aware retrieval.
- **LiteLLM** prevents provider lock-in and standardizes model access.
- **Phoenix + OpenTelemetry** make the learning loop measurable instead of aspirational.
- **Temporal** becomes important once background maintenance and replay jobs matter.

This stack keeps CLARKE:
- modular
- observable
- tenant-safe
- incrementally shippable
- production-oriented

---

## Repository Layout

Suggested top-level layout:

```text
clarke/
├── README.md
├── pyproject.toml
├── .env.example
├── docker-compose.yml
├── Makefile
├── alembic.ini
├── migrations/
├── docs/
│   ├── architecture/
│   │   ├── brokered-context-memory-system-spec.md
│   │   ├── brokered-context-memory-system-spec-expanded.md
│   │   ├── brokered-context-memory-system-spec-expanded-updated.md
│   │   ├── brokered-context-memory-system-spec-expanded-updated-multi-agent.md
│   │   └── multi-agent-hierarchy-support-addendum.md
│   ├── product/
│   ├── runbooks/
│   ├── adr/
│   └── prompts/
├── clarke/
│   ├── __init__.py
│   ├── api/
│   │   ├── app.py
│   │   ├── deps.py
│   │   ├── middleware.py
│   │   ├── routes/
│   │   │   ├── query.py
│   │   │   ├── feedback.py
│   │   │   ├── replay.py
│   │   │   ├── health.py
│   │   │   └── admin.py
│   │   └── schemas/
│   │       ├── query.py
│   │       ├── retrieval.py
│   │       ├── context.py
│   │       ├── feedback.py
│   │       ├── agents.py
│   │       └── common.py
│   ├── broker/
│   │   ├── service.py
│   │   ├── contracts.py
│   │   ├── policy.py
│   │   ├── budget.py
│   │   ├── lineage.py
│   │   └── degraded_mode.py
│   ├── graph/
│   │   ├── workflow.py
│   │   ├── state.py
│   │   ├── nodes/
│   │   │   ├── validate_request.py
│   │   │   ├── enforce_auth_and_budget.py
│   │   │   ├── extract_features.py
│   │   │   ├── build_candidate_retrieval_plan.py
│   │   │   ├── check_dependency_health.py
│   │   │   ├── select_execution_mode.py
│   │   │   ├── run_semantic_retrieval.py
│   │   │   ├── run_graph_retrieval.py
│   │   │   ├── fetch_canonical_policy.py
│   │   │   ├── fetch_structured_decisions.py
│   │   │   ├── rerank_candidates.py
│   │   │   ├── compose_context_pack.py
│   │   │   ├── count_exact_tokens.py
│   │   │   ├── call_answer_model.py
│   │   │   ├── inspect_for_context_request.py
│   │   │   ├── inspect_for_subagent_spawn.py
│   │   │   ├── validate_context_request.py
│   │   │   ├── validate_subagent_spawn.py
│   │   │   ├── run_second_pass_retrieval.py
│   │   │   ├── compose_second_pass_context.py
│   │   │   ├── create_subagent_instance.py
│   │   │   ├── build_inherited_context_pack.py
│   │   │   ├── persist_agent_lineage.py
│   │   │   ├── consume_subagent_result.py
│   │   │   ├── attribute_answer.py
│   │   │   ├── persist_episode.py
│   │   │   ├── emit_traces_and_metrics.py
│   │   │   └── garbage_collect_subagent.py
│   │   └── registry.py
│   ├── retrieval/
│   │   ├── planner/
│   │   │   ├── planner.py
│   │   │   ├── templates.py
│   │   │   ├── scoring.py
│   │   │   └── exploration.py
│   │   ├── qdrant/
│   │   │   ├── client.py
│   │   │   ├── search.py
│   │   │   └── filters.py
│   │   ├── neo4j/
│   │   │   ├── client.py
│   │   │   ├── traversal.py
│   │   │   └── graphrag.py
│   │   ├── rerank/
│   │   │   ├── cross_encoder.py
│   │   │   └── llm_reranker.py
│   │   └── composer/
│   │       ├── anchors.py
│   │       ├── dedupe.py
│   │       ├── budgeter.py
│   │       └── renderer.py
│   ├── memory/
│   │   ├── models.py
│   │   ├── episodic.py
│   │   ├── semantic.py
│   │   ├── decisions.py
│   │   ├── policy.py
│   │   └── inheritance.py
│   ├── agents/
│   │   ├── runtime.py
│   │   ├── spawn.py
│   │   ├── handles.py
│   │   ├── lifecycle.py
│   │   └── results.py
│   ├── ingestion/
│   │   ├── documents.py
│   │   ├── chunking.py
│   │   ├── redaction.py
│   │   ├── embeddings.py
│   │   └── graph_build.py
│   ├── learning/
│   │   ├── attribution.py
│   │   ├── usefulness.py
│   │   ├── weights.py
│   │   ├── clustering.py
│   │   └── proto_classes.py
│   ├── llm/
│   │   ├── gateway.py
│   │   ├── prompts.py
│   │   ├── token_counting.py
│   │   └── contracts.py
│   ├── storage/
│   │   ├── postgres/
│   │   │   ├── models.py
│   │   │   ├── repositories/
│   │   │   └── migrations/
│   │   ├── qdrant/
│   │   └── neo4j/
│   ├── evals/
│   │   ├── phoenix.py
│   │   ├── groundedness.py
│   │   ├── hallucinated_constraints.py
│   │   └── replay.py
│   ├── telemetry/
│   │   ├── tracing.py
│   │   ├── metrics.py
│   │   └── logging.py
│   ├── jobs/
│   │   ├── temporal_app.py
│   │   ├── ingestion_jobs.py
│   │   ├── clustering_jobs.py
│   │   ├── replay_jobs.py
│   │   └── cleanup_jobs.py
│   ├── settings.py
│   └── utils/
│       ├── ids.py
│       ├── time.py
│       ├── json.py
│       └── errors.py
├── tests/
│   ├── api/
│   ├── broker/
│   ├── graph/
│   ├── retrieval/
│   ├── learning/
│   ├── agents/
│   ├── integration/
│   └── fixtures/
└── scripts/
    ├── seed_dev_data.py
    ├── run_local_stack.py
    ├── replay_eval.py
    └── backfill_embeddings.py
```

---

## Project Layout Guidance

A few layout rules matter:

### 1. Keep contracts explicit
Request/response schemas, broker contracts, retrieval contracts, and structured model outputs should all be explicit and versioned.

### 2. Separate orchestration from implementation
LangGraph nodes should stay thin and delegate business logic to domain services where possible.

### 3. Keep storage concerns isolated
PostgreSQL, Qdrant, and Neo4j access should be cleanly separated behind client/repository layers.

### 4. Treat prompts like code
Prompt templates, constitutional prompt versions, and structured output instructions should be versioned, reviewed, and tested.

### 5. Keep learning logic out of the request handlers
Online request flow should emit signals. Weight updates, clustering, and replay jobs should primarily happen in background workflows.

---

## Development Phases

Recommended implementation order:

### Phase 1 — Functional broker
- FastAPI API
- LangGraph request flow
- LiteLLM integration
- PostgreSQL persistence
- typed schemas and trace wiring

### Phase 2 — Secure semantic retrieval
- document ingestion
- redaction pipeline
- embeddings
- Qdrant hybrid search
- cross-encoder reranking
- context composer
- exact token counting

### Phase 3 — Learning loop
- usefulness attribution
- retrieval weight tuning
- replay evals
- Phoenix integration
- useful-context-ratio metrics

### Phase 4 — Graph memory
- Neo4j graph model
- convergence-anchor retrieval
- decision lineage
- graph-aware retrieval blending

### Phase 5 — Emergent taxonomy
- proto-class clustering
- route improvement from learned classes
- admin tools for merge/split/promotion

### Phase 6 — Bounded multi-agent support
- structured `SUBAGENT_SPAWN`
- runtime sub-agent lifecycle
- inherited context packs
- child result ingestion
- lineage and cleanup

---

## Data and Security Expectations

CLARKE should be built with production-grade boundaries from the beginning.

### Required guarantees
- tenant isolation across all stores
- row-level security in PostgreSQL
- tenant-scoped filters in Qdrant
- tenant/project scoping in Neo4j traversals
- audit logging for memory writes and policy changes
- encrypted raw sensitive artifacts
- redacted retrieval indexes
- policy approval workflow before canonical activation

### Important rule
**A parent agent can request memory for a sub-agent, but the broker is the only authority that can approve and assemble that memory.**

---

## Model Contracts

CLARKE relies on structured model outputs. The core ones are:

- `CONTEXT_REQUEST`
- `SUBAGENT_SPAWN`
- `SUBAGENT_RESULT`

These should be treated as stable internal protocol contracts.

---

## Retrieval Philosophy

CLARKE is not “just RAG.”

It is:
- retrieval planning
- source weighting
- trust-aware composition
- exact token budgeting
- provenance-preserving context assembly
- post-answer attribution
- outcome-driven improvement

The retrieval system should optimize for:

**useful context per token**

not just raw recall or similarity.

---

## Metrics That Matter

At minimum, CLARKE should track:

- request latency
- degraded mode rate
- retrieval precision proxy
- context waste ratio
- useful context ratio
- answer groundedness
- hallucinated constraint rate
- source usefulness by type
- retrieval plan usefulness
- spawn requested vs approved
- spawn usefulness vs direct retrieval
- proto-class stability over time

---

## Local Development

Suggested local stack:
- PostgreSQL
- Qdrant
- Neo4j
- Phoenix
- optional Temporal
- mock or real LiteLLM provider configuration

Typical local workflow:
1. start local infra with Docker Compose
2. apply database migrations
3. seed development data
4. run broker API
5. ingest a small document corpus
6. run sample queries
7. inspect traces, retrieval outputs, and evaluations

---

## Environment Variables

A minimal `.env.example` should include keys like:

```env
CLARKE_ENV=development
CLARKE_LOG_LEVEL=debug

POSTGRES_URL=
QDRANT_URL=
NEO4J_URI=
NEO4J_USERNAME=
NEO4J_PASSWORD=

LITELLM_MASTER_KEY=
DEFAULT_ANSWER_MODEL=
DEFAULT_ROUTER_MODEL=
DEFAULT_EVAL_MODEL=

OTEL_EXPORTER_OTLP_ENDPOINT=
PHOENIX_ENDPOINT=

ENABLE_TEMPORAL=false
TEMPORAL_ADDRESS=

MAX_RETRIEVAL_LOOPS=1
MAX_SUBAGENT_DEPTH=5
MAX_ACTIVE_SUBAGENTS_PER_ROOT=10
DEFAULT_REQUEST_TIMEOUT_MS=800
```

---

## Suggested README Sections to Keep Updated

As the project evolves, keep these sections current:

- architecture summary
- stack/tool choices
- setup instructions
- environment variables
- repo layout
- development phases
- protocol contracts
- security guarantees
- observability expectations

---

## Naming Notes

**CLARKE** stands for:

**Cognitive Learning Augmentation Retrieval Knowledge Engine**

The name should represent the system as:
- a cognitive broker
- a retrieval engine
- a memory and knowledge coordinator
- a learning loop, not just a static store

---

## Initial Deliverables

A sensible first milestone for CLARKE is:

- working `/query` flow
- typed broker contracts
- PostgreSQL-backed request and episode persistence
- LiteLLM model call path
- simple document ingestion
- Qdrant-backed retrieval
- cross-encoder reranking
- context composition with exact token budgeting
- OpenTelemetry traces
- Phoenix evaluation hookup

That gets CLARKE to a useful, inspectable MVP without overbuilding.

---

## Contribution Guidance

When contributing to CLARKE:

- keep broker contracts explicit
- do not let models directly read storage
- preserve tenant isolation in every layer
- prefer deterministic broker behavior over hidden magic
- optimize for smallest sufficient context
- log provenance for anything injected into a prompt
- treat prompt changes like code changes
- do not add agent coordination primitives casually

---

## Status

CLARKE is currently a design-driven system under active implementation planning.

The governing documents for the architecture should live under `docs/architecture/`, with this README serving as the entry point for contributors.

---

## License

Choose the project license explicitly before public release.

Recommended options:
- Apache-2.0 for broad permissive use with patent protection
- MIT for maximal simplicity
- source-available model only if commercial restrictions are intentional
