# Brokered Context Memory System
## High-Level Milestones

## Purpose

This roadmap breaks the expanded architecture spec into execution-focused milestones.
Each milestone defines:
- objective
- scope
- key deliverables
- dependencies
- exit criteria
- major risks

The intent is to give the project a practical build sequence from zero to a fully adaptive brokered context system.

---

## Cross-Cutting Requirements Added From Review

These requirements apply across the entire roadmap and should be treated as mandatory, not optional polish.

### Security, privacy, and multi-tenancy
- enforce explicit tenant isolation in **every** retrieval and persistence layer using `tenant_id` and, where relevant, `user_id` and `project_id`
- require Qdrant payload filters, Neo4j tenant-aware query predicates, and PostgreSQL row-level security policies
- add mandatory PII/sensitive-data scrubbing during document ingestion and episodic-memory creation
- store only redacted summaries in vector and graph stores; keep raw content in encrypted canonical storage with retention rules
- require append-only audit logging for every memory write, edit, cluster mutation, and policy change with `changed_by`, `changed_at`, and `reason`
- require RBAC and approval workflow for policy memory before a policy becomes canonical

### Robustness and graceful degradation
- add circuit breakers around Qdrant, Neo4j, reranker, and model gateway integrations
- support degraded serving modes, especially a **canonical-only mode** that answers from policy + decision memory when retrieval systems are unhealthy
- enforce per-node timeout budgets in the execution graph; on timeout, skip the source, mark the run as degraded, and continue if safe
- make `request_id` globally idempotent and propagate it across all storage tables and traces
- add second-pass quota controls in addition to loop count limits

### Retrieval quality and composition
- use Qdrant hybrid search where available, not pure vector search only
- support blended scoring where final retrieval score can combine semantic, lexical, graph, recency, and trust components
- use exact tokenizer-based counting for context budgets based on the actual answer model
- add semantic deduplication before prompt injection and prefer merged evidence summaries with multiple provenances
- render anchors before evidence in the prompt

### Learning loop and taxonomy stability
- add light exploration in retrieval-plan selection using epsilon-greedy or similar bounded exploration
- define clustering, promotion, merge, and split rules more concretely
- support human override endpoints for proto-class merge, split, rename, and promotion
- version prompts, planner weights, embeddings, graph builds, and clustering runs

### Observability and evals
- add a top-level metric: **Useful Context Ratio** = attributed injected tokens / total injected tokens
- add a hallucinated-constraint check to evals
- allow feedback to target specific retrieved items, not only whole episodes
- carry `degraded_mode` through the online state machine and telemetry

---

## Milestone 0 — Foundation and Control Plane

### Objective
Establish the baseline service, repository structure, local development workflow, security model, and observability scaffolding needed for all later work.

### Scope
- repository structure
- environment/config management
- local and dev deployment setup
- base service bootstrapping
- tracing/logging scaffolding
- initial CI/CD and test harness
- baseline tenant and security model

### Key deliverables
- FastAPI service skeleton
- configuration system for provider keys, DB connections, and feature flags
- base OpenTelemetry instrumentation
- health endpoint and service lifecycle wiring
- Docker Compose or equivalent local environment
- CI pipeline with lint, tests, and type checks
- initial architecture decision records
- global `request_id` generation and propagation rules
- baseline tenant model with `tenant_id`, `project_id`, and `user_id` conventions
- rate limiting and per-user budget middleware scaffold

### Dependencies
- none

### Exit criteria
- service boots reliably in local/dev
- tracing and structured logs are emitted
- configuration and secrets handling are standardized
- CI passes on a fresh checkout
- request identity and correlation are consistent end-to-end
- basic authn/authz boundaries are defined in writing

### Major risks
- skipping observability early and losing debuggability later
- inconsistent environment setup across contributors
- failing to define tenancy early and having to retrofit it later

---

## Milestone 1 — Functional Broker MVP

### Objective
Ship a working broker that accepts a user query, performs a basic retrieval pass, builds an initial context pack, calls the LLM, and returns an answer.

### Scope
- `/query` API
- LiteLLM integration
- LangGraph execution flow
- minimal context composer
- PostgreSQL persistence for request and response episodes
- degraded-mode scaffolding

### Key deliverables
- typed request/response schemas
- LangGraph online flow with checkpoints
- first-pass context injection
- answer model integration through LiteLLM
- persistence of query, retrieval plan, injected context, and answer summary
- bounded loop support disabled or stubbed for now
- LangGraph state includes `degraded_mode: bool`
- prompt version capture on every run
- canonical-only fallback path defined but not yet fully powered

### Dependencies
- Milestone 0
- PostgreSQL
- LiteLLM
- LangGraph

### Exit criteria
- a user query can be processed end-to-end
- the system stores an auditable episode record
- context injection is happening before the model call
- the broker can run in a stable staging environment
- every run records request ID, prompt version, model, and degraded mode status

### Major risks
- overdesigning the planner before basic end-to-end flow works
- allowing too much unstructured prompt assembly too early
- not reserving a clean fallback path for degraded operation

---

## Milestone 2 — Document Ingestion and Semantic Memory

### Objective
Add document ingestion and semantic retrieval so the broker can retrieve useful context from uploaded or indexed sources.

### Scope
- Unstructured ingestion pipeline
- chunking and provenance preservation
- embeddings pipeline
- Qdrant integration
- retrieval candidate generation
- redaction and retention rules

### Key deliverables
- ingest pipeline for PDF, Markdown, DOCX, HTML, and TXT
- normalized chunk schema with provenance
- mandatory PII/sensitive-data scrubber before vector/graph persistence
- encrypted raw document storage with retention metadata
- embedding job and Qdrant indexing workflow
- semantic retrieval endpoint/service
- metadata filtering by tenant, source type, user, project, and recency
- retrieval candidate objects normalized for broker use
- immutable audit records for ingest and re-ingest actions

### Dependencies
- Milestone 1
- Unstructured
- Qdrant
- embedding model pipeline

### Exit criteria
- documents can be ingested and searched semantically
- retrieved chunks preserve source provenance
- broker can use semantic retrieval results in first-pass context packs
- vector store contains only redacted, tenant-scoped content
- retention and deletion hooks exist for ingested material

### Major risks
- poor chunking strategy that destroys semantic coherence
- weak provenance making debugging and trust hard
- accidental storage of raw sensitive content in retrieval stores

---

## Milestone 3 — Reranking and Context Budgeting

### Objective
Improve retrieval precision and reduce context waste by reranking candidates and enforcing context composition rules.

### Scope
- hybrid semantic + lexical retrieval
- cross-encoder reranking
- exact token counting
- context deduplication
- source-aware budgeting
- evidence vs anchor separation

### Key deliverables
- Qdrant hybrid search enabled where supported
- Sentence Transformers cross-encoder reranker integration
- optional final micro-reranker hook for design/tradeoff queries on top-N candidates
- candidate reranking stage after semantic retrieval
- context composer with tokenizer-accurate budgets by source type and task features
- semantic deduplication and overlap suppression
- provenance-preserving evidence formatting
- anchor-first prompt rendering
- initial Useful Context Ratio metric

### Dependencies
- Milestone 2
- reranking model
- tokenizer access through answer-model stack

### Exit criteria
- broker injects a smaller, better-ranked context pack
- irrelevant retrieval items are reduced
- context waste is measurable
- actual token counts match the target model tokenizer
- duplicate evidence is merged or suppressed before injection

### Major risks
- reranking cost becoming too high on the hot path
- context composer mixing policy, evidence, and transient state together
- relying on estimated token counts and causing prompt overflows

---

## Milestone 4 — Structured Context Request Loop

### Objective
Allow the model to request additional context in a controlled way after the first pass.

### Scope
- structured `CONTEXT_REQUEST` contract
- request validation
- second-pass retrieval and answer flow
- hard loop limits
- quota enforcement

### Key deliverables
- JSON schema for context requests
- broker validation for requested sources and constraints
- second-pass LangGraph branch
- loop counter and hard stop policy
- source-specific retrieval request handlers
- per-user and per-tenant second-pass quotas
- telemetry for loop rate and second-pass usefulness
- rejection reasons and degraded fallback behavior for invalid requests

### Dependencies
- Milestone 3
- stable retrieval services
- LiteLLM structured output support

### Exit criteria
- model can request more context through strict JSON only
- broker can satisfy a valid request and run one second-pass call
- invalid or overly broad requests are rejected safely
- second-pass usage is bounded by both technical and cost controls

### Major risks
- the model over-requesting context
- turning the system into an unbounded agent loop
- abuse or runaway cost through repeated escalation attempts

---

## Milestone 5 — Retrieval Episode Logging and Evaluation

### Objective
Capture enough structured evidence about each retrieval episode to measure whether the system is improving.

### Scope
- detailed retrieval episode logging
- answer attribution scaffolding
- eval datasets and dashboards
- Phoenix integration
- immutable audit trails

### Key deliverables
- retrieval episode schema finalized in PostgreSQL
- retrieved vs injected vs used item tracking
- item-level feedback hooks in `/feedback`
- answer attribution heuristics
- Phoenix tracing and evaluation integration
- dashboards for latency, usefulness, grounding, waste, and hallucinated constraints
- replay dataset export format
- append-only memory-write audit log schema

### Dependencies
- Milestone 4
- PostgreSQL
- OpenTelemetry
- Phoenix

### Exit criteria
- each online run can be inspected end-to-end
- usefulness and waste metrics are available
- replay-ready episode data exists for optimization work
- Useful Context Ratio and hallucinated-constraint signals are tracked
- writes to memory-bearing systems are audit visible

### Major risks
- weak attribution making optimization signals noisy
- missing metadata making offline replay unreliable
- logging too little to diagnose retrieval regressions later

---

## Milestone 6 — Query-to-Retrieval Optimization Layer

### Objective
Teach the system to improve how it translates raw user queries into retrieval requests.

### Scope
- retrieval planner weights
- source priors
- rewrite template weighting
- online usefulness updates
- offline replay experiments
- bounded exploration
- blended retrieval scoring

### Key deliverables
- structured retrieval request generator
- source/task weighting tables
- rewrite template inventory
- graph/semantic blending score model
- online weight update loop
- replay harness for comparing retrieval plans
- epsilon-greedy exploration with decay and safety caps
- first ranking policy for smallest sufficient context

### Dependencies
- Milestone 5
- stable eval signals

### Exit criteria
- broker can generate multiple retrieval request candidates
- the system can update weights based on usefulness signals
- replay can compare planner versions against historical runs
- low-rate exploration is active and observable
- blending weights are tunable and versioned

### Major risks
- optimizing for raw relevance instead of useful context per token
- overfitting planner behavior to narrow workloads
- exploration causing outsized cost without safety caps

---

## Milestone 7 — Graph Memory and Convergence Retrieval

### Objective
Add graph-aware memory so the system can retrieve leaf nodes first, then identify shared anchors and relationship-aware context.

### Scope
- Neo4j data model
- graph ingest from memory and docs
- leaf-first retrieval
- convergence-anchor discovery
- graph-aware context summaries
- tenant-aware graph constraints

### Key deliverables
- Neo4j schema for entities, concepts, docs, summaries, decisions, and policies
- tenant-scoped graph query utilities and mandatory query predicates
- graph edge creation pipeline
- graph neighborhood query utilities
- bottom-up retrieval flow: leaves first, anchors second
- anchor summarization for prompt-safe context injection
- graph-plus-semantic blended ranking
- `last_retrieved_at` tracking on nodes/edges used for maintenance and staleness jobs

### Dependencies
- Milestone 3 for retrieval quality
- Milestone 5 for observability
- Neo4j
- graph ingest jobs

### Exit criteria
- system can find relevant leaf nodes and identify useful shared anchors
- graph retrieval contributes meaningful evidence to initial context packs
- graph context is summarized, not dumped raw
- graph queries are tenant safe by construction
- staleness/pruning signals exist for graph maintenance

### Major risks
- graph schema becoming taxonomy theater instead of retrieval utility
- broad graph traversal increasing latency and noise
- unsafe tenant joins in graph retrieval

---

## Milestone 8 — Decision Memory and Canonical Policy Layer

### Objective
Separate durable truth and policy from generic memory so the broker can resolve conflicts predictably.

### Scope
- decision memory model
- canonical policy model
- truth precedence rules
- conflict resolution behavior
- RBAC and approval workflow

### Key deliverables
- policy node schema and storage model
- decision record schema with rationale and status
- precedence model for policy vs facts vs episodic memory
- retrieval hooks for decision lineage and policy lookup
- prompt rules for trust ordering
- owner/approver fields for policy nodes
- approval workflow before policy becomes canonical
- explicit conflict language in the prompt templates

### Dependencies
- Milestone 5
- PostgreSQL
- optionally Milestone 7 for graph lineage

### Exit criteria
- broker can inject canonical policy fragments separately from evidence
- conflicting retrieved items can be ordered predictably
- architecture and planning queries can pull prior decisions as first-class context
- policy promotion requires explicit approval
- prompt precedence rules are versioned and auditable

### Major risks
- mixing policy with evidence in ways the model cannot distinguish
- stale decisions being treated as canonical without status controls
- policy drift without ownership and approval metadata

---

## Milestone 9 — Emergent Taxonomy and Proto-Class System

### Objective
Allow useful classifications to emerge from repeated retrieval behavior instead of forcing a mature taxonomy from the start.

### Scope
- query feature extraction
- clustering of retrieval episodes
- proto-class storage
- promotion, merge, and split rules
- human override controls

### Key deliverables
- feature extraction pipeline for query and retrieval behavior
- proto-class schema in PostgreSQL
- clustering jobs over historical episodes
- HDBSCAN or equivalent clustering strategy documented and implemented
- label candidate generation
- promotion criteria for operational classes, including stability and member thresholds
- merge and split rules with audit history
- admin endpoints or tooling for force-merge, force-split, rename, and promotion

### Dependencies
- Milestone 6
- Milestone 5
- ideally Milestone 7 for relational signal enrichment
- background jobs

### Exit criteria
- the system can identify repeated useful retrieval patterns
- proto-classes can influence routing without being treated as hard truth
- stable classes improve planner behavior measurably
- human override exists for early taxonomy correction

### Major risks
- premature hard-coding of labels
- classes that sound good but do not improve retrieval outcomes
- unstable clusters being promoted too early

---

## Milestone 10 — Background Workflows and Continuous Learning

### Objective
Move heavy system maintenance and learning tasks out of the hot path into durable background workflows.

### Scope
- Temporal workflows
- re-embedding
- graph rebuilds
- replay eval runs
- reweighting and class maintenance
- pruning and retention

### Key deliverables
- Temporal worker setup
- durable jobs for ingest, reindexing, and clustering
- replay workflow definitions
- scheduled weight recomputation
- class maintenance jobs
- graph pruning and stale-edge cleanup jobs
- recovery and retry policies for background pipelines
- versioned rollout and rollback plans for prompts, embeddings, planner weights, and graph builds

### Dependencies
- Milestones 5 through 9
- Temporal

### Exit criteria
- heavy maintenance no longer blocks online serving
- background learning workflows are resumable and observable
- model, embedding, and planner upgrades can be replay-tested safely
- stale graph relationships and retired artifacts can be pruned safely
- rollback paths exist for major learned-state regressions

### Major risks
- background jobs mutating live state without sufficient versioning
- poor idempotency leading to duplicate or corrupted state
- retention jobs deleting material still needed for audit or compliance

---

## Milestone 11 — Production Hardening and Governance

### Objective
Make the system reliable, governable, and safe enough for real production use.

### Scope
- security
- auth and tenancy
- rate limiting
- prompt and retrieval safety
- disaster recovery
- governance tooling
- fallback behavior

### Key deliverables
- authn/authz model for users, projects, and data scopes
- PostgreSQL RLS policies and tenant isolation validation tests
- tenant isolation rules for Qdrant and Neo4j with automated contract tests
- retention and deletion workflows
- PII handling rules for memory and docs
- rate limiting and abuse controls
- per-user token budget controls
- backup and restore procedures
- versioning for prompts, planner weights, embeddings, and graph builds
- governance dashboard for policy, decisions, and class maintenance
- service health policies, circuit breakers, and degraded-mode routing matrix
- retrieval timeout budgets documented and enforced

### Dependencies
- all prior milestones

### Exit criteria
- system can be operated with clear security and governance boundaries
- rollback/versioning exists for critical models and indices
- production SLOs and runbooks are defined
- degraded modes are tested and documented
- tenant isolation has automated verification across all stores

### Major risks
- treating retrieval data as harmless when it may contain sensitive material
- lacking versioned rollback across planner, graph, and embedding state
- shipping without tested degraded behavior and recovery runbooks

---

## Milestone 12 — Optional Advanced Capabilities

### Objective
Layer on advanced capabilities once the core brokered context system is stable and measurable.

### Scope
- vLLM self-hosted utility models
- advanced graph neighborhood requests
- richer answer attribution
- human-in-the-loop class naming and policy review
- adaptive source routing by tenant/project

### Key deliverables
- self-hosted models for rewrite/eval/classification tasks
- neighborhood summary request primitives
- improved attribution and relevance explanations
- human review tools for proto-class promotion and policy edits
- advanced planner experimentation framework
- documented LiteLLM model-role map and temperature defaults by role

### Dependencies
- production-stable core system

### Exit criteria
- advanced features measurably improve cost, latency, or answer quality
- added complexity remains observable and controllable
- model-role tuning is documented and traceable

### Major risks
- adding sophistication before core usefulness is proven
- feature creep diluting the broker’s core design principles

---

## Cross-Milestone Success Metrics

These should be tracked throughout the program.

### Quality metrics
- answer groundedness
- retrieval usefulness score
- context waste ratio
- Useful Context Ratio
- user correction rate
- answer acceptance / productive follow-up rate
- hallucinated constraint rate

### Performance metrics
- p50 and p95 end-to-end latency
- retrieval latency by source type
- reranker latency
- loop invocation rate
- second-pass success rate
- degraded-mode activation rate

### Learning metrics
- planner improvement over replay baselines
- usefulness by source type
- usefulness by rewrite template
- usefulness by graph strategy
- proto-class stability over time
- exploration win rate

### Security and governance metrics
- tenant-isolation test pass rate
- redaction false-negative incident count
- policy approval lead time
- audit log completeness

---

## Recommended Build Order

1. Milestone 0 — Foundation and Control Plane
2. Milestone 1 — Functional Broker MVP
3. Milestone 2 — Document Ingestion and Semantic Memory
4. Milestone 3 — Reranking and Context Budgeting
5. Milestone 4 — Structured Context Request Loop
6. Milestone 5 — Retrieval Episode Logging and Evaluation
7. Milestone 6 — Query-to-Retrieval Optimization Layer
8. Milestone 7 — Graph Memory and Convergence Retrieval
9. Milestone 8 — Decision Memory and Canonical Policy Layer
10. Milestone 9 — Emergent Taxonomy and Proto-Class System
11. Milestone 10 — Background Workflows and Continuous Learning
12. Milestone 11 — Production Hardening and Governance
13. Milestone 12 — Optional Advanced Capabilities

---

## Immediate Priority Adjustments From Review

Before exposing the system to real production traffic, prioritize these items even if it slightly delays higher-level capability work:

1. tenant isolation, privacy scrubbing, audit logging, and policy RBAC
2. circuit breakers, retrieval timeouts, degraded-mode routing, and idempotency
3. hybrid search, exact token budgeting, and semantic deduplication
4. exploration controls and concrete proto-class clustering/promotion rules
5. deeper ops polish and advanced optional features
