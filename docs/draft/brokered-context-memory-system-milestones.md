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

## Milestone 0 — Foundation and Control Plane

### Objective
Establish the baseline service, repository structure, local development workflow, and observability scaffolding needed for all later work.

### Scope
- repository structure
- environment/config management
- local and dev deployment setup
- base service bootstrapping
- tracing/logging scaffolding
- initial CI/CD and test harness

### Key deliverables
- FastAPI service skeleton
- configuration system for provider keys, DB connections, and feature flags
- base OpenTelemetry instrumentation
- health endpoint and service lifecycle wiring
- Docker Compose or equivalent local environment
- CI pipeline with lint, tests, and type checks
- initial architecture decision records

### Dependencies
- none

### Exit criteria
- service boots reliably in local/dev
- tracing and structured logs are emitted
- configuration and secrets handling are standardized
- CI passes on a fresh checkout

### Major risks
- skipping observability early and losing debuggability later
- inconsistent environment setup across contributors

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

### Key deliverables
- typed request/response schemas
- LangGraph online flow with checkpoints
- first-pass context injection
- answer model integration through LiteLLM
- persistence of query, retrieval plan, injected context, and answer summary
- bounded loop support disabled or stubbed for now

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

### Major risks
- overdesigning the planner before basic end-to-end flow works
- allowing too much unstructured prompt assembly too early

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

### Key deliverables
- ingest pipeline for PDF, Markdown, DOCX, HTML, and TXT
- normalized chunk schema with provenance
- embedding job and Qdrant indexing workflow
- semantic retrieval endpoint/service
- metadata filtering by source type, user, project, and recency
- retrieval candidate objects normalized for broker use

### Dependencies
- Milestone 1
- Unstructured
- Qdrant
- embedding model pipeline

### Exit criteria
- documents can be ingested and searched semantically
- retrieved chunks preserve source provenance
- broker can use semantic retrieval results in first-pass context packs

### Major risks
- poor chunking strategy that destroys semantic coherence
- weak provenance making debugging and trust hard

---

## Milestone 3 — Reranking and Context Budgeting

### Objective
Improve retrieval precision and reduce context waste by reranking candidates and enforcing context composition rules.

### Scope
- cross-encoder reranking
- context deduplication
- source-aware budgeting
- evidence vs anchor separation

### Key deliverables
- Sentence Transformers cross-encoder reranker integration
- candidate reranking stage after semantic retrieval
- context composer with token budgets by source type
- deduplication and overlap suppression
- provenance-preserving evidence formatting
- initial context waste metrics

### Dependencies
- Milestone 2
- reranking model

### Exit criteria
- broker injects a smaller, better-ranked context pack
- irrelevant retrieval items are reduced
- context waste is measurable

### Major risks
- reranking cost becoming too high on the hot path
- context composer mixing policy, evidence, and transient state together

---

## Milestone 4 — Structured Context Request Loop

### Objective
Allow the model to request additional context in a controlled way after the first pass.

### Scope
- structured `CONTEXT_REQUEST` contract
- request validation
- second-pass retrieval and answer flow
- hard loop limits

### Key deliverables
- JSON schema for context requests
- broker validation for requested sources and constraints
- second-pass LangGraph branch
- loop counter and hard stop policy
- source-specific retrieval request handlers
- telemetry for loop rate and second-pass usefulness

### Dependencies
- Milestone 3
- stable retrieval services
- LiteLLM structured output support

### Exit criteria
- model can request more context through strict JSON only
- broker can satisfy a valid request and run one second-pass call
- invalid or overly broad requests are rejected safely

### Major risks
- the model over-requesting context
- turning the system into an unbounded agent loop

---

## Milestone 5 — Retrieval Episode Logging and Evaluation

### Objective
Capture enough structured evidence about each retrieval episode to measure whether the system is improving.

### Scope
- detailed retrieval episode logging
- answer attribution scaffolding
- eval datasets and dashboards
- Phoenix integration

### Key deliverables
- retrieval episode schema finalized in PostgreSQL
- retrieved vs injected vs used item tracking
- answer attribution heuristics
- Phoenix tracing and evaluation integration
- dashboards for latency, usefulness, grounding, and waste
- replay dataset export format

### Dependencies
- Milestone 4
- PostgreSQL
- OpenTelemetry
- Phoenix

### Exit criteria
- each online run can be inspected end-to-end
- usefulness and waste metrics are available
- replay-ready episode data exists for optimization work

### Major risks
- weak attribution making optimization signals noisy
- missing metadata making offline replay unreliable

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

### Key deliverables
- structured retrieval request generator
- source/task weighting tables
- rewrite template inventory
- online weight update loop
- replay harness for comparing retrieval plans
- first ranking policy for smallest sufficient context

### Dependencies
- Milestone 5
- stable eval signals

### Exit criteria
- broker can generate multiple retrieval request candidates
- the system can update weights based on usefulness signals
- replay can compare planner versions against historical runs

### Major risks
- optimizing for raw relevance instead of useful context per token
- overfitting planner behavior to narrow workloads

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

### Key deliverables
- Neo4j schema for entities, concepts, docs, summaries, decisions, and policies
- graph edge creation pipeline
- graph neighborhood query utilities
- bottom-up retrieval flow: leaves first, anchors second
- anchor summarization for prompt-safe context injection
- graph-plus-semantic blended ranking

### Dependencies
- Milestone 3 for retrieval quality
- Milestone 5 for observability
- Neo4j
- graph ingest jobs

### Exit criteria
- system can find relevant leaf nodes and identify useful shared anchors
- graph retrieval contributes meaningful evidence to initial context packs
- graph context is summarized, not dumped raw

### Major risks
- graph schema becoming taxonomy theater instead of retrieval utility
- broad graph traversal increasing latency and noise

---

## Milestone 8 — Decision Memory and Canonical Policy Layer

### Objective
Separate durable truth and policy from generic memory so the broker can resolve conflicts predictably.

### Scope
- decision memory model
- canonical policy model
- truth precedence rules
- conflict resolution behavior

### Key deliverables
- policy node schema and storage model
- decision record schema with rationale and status
- precedence model for policy vs facts vs episodic memory
- retrieval hooks for decision lineage and policy lookup
- prompt rules for trust ordering

### Dependencies
- Milestone 5
- PostgreSQL
- optionally Milestone 7 for graph lineage

### Exit criteria
- broker can inject canonical policy fragments separately from evidence
- conflicting retrieved items can be ordered predictably
- architecture and planning queries can pull prior decisions as first-class context

### Major risks
- mixing policy with evidence in ways the model cannot distinguish
- stale decisions being treated as canonical without status controls

---

## Milestone 9 — Emergent Taxonomy and Proto-Class System

### Objective
Allow useful classifications to emerge from repeated retrieval behavior instead of forcing a mature taxonomy from the start.

### Scope
- query feature extraction
- clustering of retrieval episodes
- proto-class storage
- promotion, merge, and split rules

### Key deliverables
- feature extraction pipeline for query and retrieval behavior
- proto-class schema in PostgreSQL
- clustering jobs over historical episodes
- label candidate generation
- promotion criteria for operational classes
- merge and split rules with audit history

### Dependencies
- Milestone 6
- Milestone 5
- ideally Milestone 7 for relational signal enrichment
- background jobs

### Exit criteria
- the system can identify repeated useful retrieval patterns
- proto-classes can influence routing without being treated as hard truth
- stable classes improve planner behavior measurably

### Major risks
- premature hard-coding of labels
- classes that sound good but do not improve retrieval outcomes

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

### Key deliverables
- Temporal worker setup
- durable jobs for ingest, reindexing, and clustering
- replay workflow definitions
- scheduled weight recomputation
- class maintenance jobs
- recovery and retry policies for background pipelines

### Dependencies
- Milestones 5 through 9
- Temporal

### Exit criteria
- heavy maintenance no longer blocks online serving
- background learning workflows are resumable and observable
- model, embedding, and planner upgrades can be replay-tested safely

### Major risks
- background jobs mutating live state without sufficient versioning
- poor idempotency leading to duplicate or corrupted state

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

### Key deliverables
- authn/authz model for users, projects, and data scopes
- tenant isolation rules
- retention and deletion workflows
- PII handling rules for memory and docs
- rate limiting and abuse controls
- backup and restore procedures
- versioning for prompts, planner weights, embeddings, and graph builds
- governance dashboard for policy, decisions, and class maintenance

### Dependencies
- all prior milestones

### Exit criteria
- system can be operated with clear security and governance boundaries
- rollback/versioning exists for critical models and indices
- production SLOs and runbooks are defined

### Major risks
- treating retrieval data as harmless when it may contain sensitive material
- lacking versioned rollback across planner, graph, and embedding state

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

### Dependencies
- production-stable core system

### Exit criteria
- advanced features measurably improve cost, latency, or answer quality
- added complexity remains observable and controllable

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
- user correction rate
- answer acceptance / productive follow-up rate

### Performance metrics
- p50 and p95 end-to-end latency
- retrieval latency by source type
- reranker latency
- loop invocation rate
- second-pass success rate

### Learning metrics
- planner improvement over replay baselines
- usefulness by source type
- usefulness by rewrite template
- usefulness by graph strategy
- proto-class stability over time

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

## One-Line Program Summary

Build the system in this order:
**first make it work, then make retrieval precise, then make it measurable, then make it adaptive, then make it relational, then make it governable.**
