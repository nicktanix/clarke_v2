# Brokered Context Memory System
## Expanded Reference Architecture Specification

## 1. Purpose

This system replaces static runtime context files with a **brokered context engine** that:

- interprets a user request or parent-agent request
- builds the smallest sufficient initial context pack
- calls the LLM once with that context
- allows the LLM to request additional context in a structured way
- allows the LLM to request creation of a bounded runtime sub-agent through a structured broker-mediated contract
- learns over time which retrieval plans are useful
- develops an emergent classification system from usage rather than requiring a perfect ontology on day one

The system now includes **first-party hierarchical multi-agent support**. Parent agents may request broker-created runtime sub-agents for well-scoped separable sub-tasks. Each sub-agent receives its own isolated, fully brokered context and memory scope tailored to the delegated task.

---

## 2. Primary Goals

### Functional goals
- inject relevant context before the first LLM call
- support structured follow-up context requests
- unify memory, docs, decisions, policy, and recent history
- support graph-aware retrieval and bottom-up convergence
- continuously improve query-to-retrieval planning
- enforce strong tenant isolation and policy governance
- support structured sub-agent spawning with automatic brokered context and memory handoff
- preserve lineage, provenance, and learning signals across agent hierarchies

### Quality goals
- low latency on the happy path
- bounded retrieval loops
- bounded sub-agent depth and bounded runtime sub-agent concurrency
- high provenance and auditability
- low context waste
- graceful operation from zero or near-zero prior memory
- progressive self-organization into useful classes
- safe degradation when dependencies fail
- exact token-budget enforcement for the target model
- isolated, inheritable memory scopes for runtime sub-agents

---

## 3. Non-goals

- fully autonomous open-ended agent behavior
- unrestricted model access to storage internals
- dumping raw graph neighborhoods into prompts by default
- replacing all canonical human-authored policy with emergent memory
- storing unredacted sensitive data in retrieval indexes
- unrestricted autonomous agent swarms
- child-to-child communication or sibling coordination in V1

---

## 4. System Overview

```text
User / Parent-Agent Query
   |
   v
Broker API (FastAPI)
   |
   v
Execution Graph (LangGraph)
   |
   +--> Query Understanding
   |
   +--> Retrieval Planner
   |
   +--> Retrieval Layer
   |      +--> Semantic + Hybrid Search (Qdrant)
   |      +--> Graph Search (Neo4j / GraphRAG)
   |      +--> Canonical Metadata (PostgreSQL)
   |      +--> Documents (Unstructured outputs)
   |
   +--> Context Composer / Budgeter
   |
   +--> LLM Gateway (LiteLLM)
   |
   +--> Optional CONTEXT_REQUEST Loop
   |
   +--> Optional SUBAGENT_SPAWN Handler
   |      +--> Validate Spawn
   |      +--> Create Runtime Agent Instance
   |      +--> Build Inherited Context Pack
   |      +--> Persist Lineage
   |      +--> Return Scoped Handle
   |
   +--> Final Answer / Sub-Agent Result
   |
   +--> Telemetry / Eval / Feedback
           +--> OpenTelemetry
           +--> Phoenix
           +--> PostgreSQL
           +--> Background Jobs (Temporal)
```

---

## 5. Core Architectural Principles

### 5.1 Broker-owned retrieval
The LLM never directly reads memory. It can only request more context through a structured schema.

### 5.2 Retrieval is multi-stage
Initial retrieval should be selective, ranked, budgeted, explainable, and tenant-safe.

### 5.3 Leaves first, anchors second
Initial context should usually be built from relevant leaf nodes first, then shared anchors or convergence concepts.

### 5.4 Memory is not one thing
The system should treat these as distinct but connected:
- working context
- episodic memory
- semantic memory
- decision memory
- document memory
- policy memory

### 5.5 Classes must be earned
The system should not require a mature taxonomy at bootstrap. It should derive useful proto-classes from repeated successful retrieval behavior.

### 5.6 Smallest sufficient context
The system should optimize for the **smallest sufficient grounded context pack**, not maximum recall.

### 5.7 Explicit trust ordering
When conflicts appear, the system must preserve and surface source precedence instead of silently blending contradictions.

### 5.8 Degrade safely
If optional retrieval subsystems fail, the system should fall back to canonical-only or reduced-context modes rather than fail open.

### 5.9 Hierarchical agent spawning with brokered handoff
Parent agents may request creation of runtime sub-agents via a structured `SUBAGENT_SPAWN` response. The broker alone creates the sub-agent instance, assembles its initial context pack from approved parent context plus explicit handoff inputs, and returns a scoped handle.

### 5.10 Sub-agents are task-scoped, broker-governed execution units
Sub-agents are ephemeral runtime instances created only for separable sub-tasks. They are not unrestricted autonomous workers, do not receive direct storage access, and do not share mutable working memory with parent agents.

### 5.11 Prefer retrieval before delegation
The system must prefer `CONTEXT_REQUEST` over `SUBAGENT_SPAWN` unless the requested work is clearly separable, well-scoped, and benefits from isolated execution.

---

## 6. Cross-Cutting Non-Functional Requirements

### 6.1 Multi-tenancy and isolation
Every retrieval and persistence path must enforce:
- `tenant_id`
- `project_id`
- `user_id` where applicable

Requirements:
- Qdrant payload filters must always include tenant constraints.
- Neo4j traversals must include tenant/project scoping in every query pattern.
- PostgreSQL must enforce row-level security for tenant-owned tables.
- Context composition must reject mixed-tenant candidate sets.
- Replay and eval jobs must preserve original tenant boundaries.
- Sub-agent inheritance and lineage must preserve tenant and project scope at every hop.

### 6.2 Security and privacy
- Raw documents may be stored encrypted, but retrieval indexes must contain **redacted** summaries/chunks by default.
- Document ingestion and episodic summarization must include PII/sensitive-data scrubbing.
- Sensitive raw artifacts must have retention controls and access tiering.
- Policy nodes must include owner, approver, approval status, and effective dates.
- Every memory write must be immutable append-only at the audit layer with `changed_by` and `reason`.
- Parent agents may request child memory sources, but the broker always re-enforces permissions, policy restrictions, sensitivity tiers, and source allowlists.

### 6.3 Reliability and degradation
- Each retrieval subsystem gets a wall-clock timeout budget.
- Retrieval failures should mark the request as `degraded_mode=true` and continue when safe.
- Circuit breakers should temporarily disable unhealthy dependencies.
- Second-pass context requests must be rate-limited and quota-controlled.
- Sub-agent spawning is disabled in canonical-only mode.
- In reduced degraded mode, sub-agent spawning is allowed only for narrow read-only tasks.

### 6.4 Cost controls
- Exact token counting must use the real tokenizer for the selected answer model.
- Per-user and per-tenant budgets must exist for:
  - first-pass prompt tokens
  - second-pass prompt tokens
  - total daily second-pass invocations
  - total active sub-agents
  - per-root-request sub-agent budget
- Retrieval planning should factor estimated token cost into ranking.
- Spawn approval must consider expected child token budget and time budget.

### 6.5 Hierarchical execution constraints
- Sub-agent depth must be bounded. Default maximum depth: `5`.
- Total active sub-agents must be quota-limited per tenant, project, and root request.
- Sub-agent creation must be budget-limited by token, time, and concurrency thresholds.
- Child-to-child communication is not allowed in V1.
- Sibling coordination primitives are out of scope for V1.

### 6.6 Memory inheritance and isolation
- Sub-agents do not share mutable working memory with parent agents.
- Sub-agents receive a broker-assembled inherited context pack plus optional broker-mediated access to approved linked memory.
- Parent-to-child handoff must follow one of these modes:
  - `copy_in`: a point-in-time context snapshot is passed to the child
  - `reference_link`: the child may retrieve only from broker-approved linked artifacts
  - `hybrid`: combines `copy_in` and `reference_link`
- Child agents may not write directly into parent memory.
- Child results may be promoted into parent-visible memory only through broker-controlled result ingestion.

### 6.7 Spawn approval policy
A `SUBAGENT_SPAWN` request may only be approved when all of the following are true:
- the requested task is clearly scoped and separable
- the task has a defined output shape
- the task cannot be more efficiently satisfied by a `CONTEXT_REQUEST`
- tenant, project, and policy constraints allow the spawn
- depth, budget, and concurrency limits allow the spawn
- the required memory sources are allowed for the child scope

---

## 7. Major Components

## 7.1 Broker API
**Technology:** FastAPI

### Responsibilities
- receive user requests
- validate schemas
- invoke orchestration flow
- expose sync and streaming endpoints
- surface trace IDs and debug info when needed
- enforce rate limits, per-user budgets, and auth
- expose agent-scoped query entry using broker-issued agent handles

### Endpoints
- `POST /query`
- `POST /feedback`
- `POST /replay`
- `POST /admin/proto-classes/{id}/promote`
- `POST /admin/proto-classes/{id}/merge`
- `POST /admin/proto-classes/{id}/split`
- `GET /health`
- `GET /trace/{id}`

### Requirements
- typed request and response contracts
- auth support
- idempotency support
- trace propagation
- streaming completion support
- per-user rate limiting middleware
- request-scoped `request_id` propagation
- support `agent_id` / sub-agent handle scoping for delegated calls

### Dependencies
- LangGraph
- PostgreSQL
- LiteLLM
- OpenTelemetry

---

## 7.2 Execution Graph
**Technology:** LangGraph

### Responsibilities
- coordinate all online steps
- persist checkpoints
- support bounded loop behavior
- support deterministic retries
- route into degraded fallback paths
- evaluate structured sub-agent spawn requests

### Online flow
1. parse request
2. enforce auth, tenant scope, and quotas
3. extract query features
4. generate retrieval plan candidates
5. evaluate dependency health and route mode
6. execute retrieval
7. compose initial context pack
8. call LLM
9. inspect result
10. if `CONTEXT_REQUEST`, validate against policy/quota, retrieve more, and run second pass
11. if `SUBAGENT_SPAWN`, validate spawn, create sub-agent instance, build inherited context, and return scoped handle
12. finalize answer or return child result
13. persist episode and telemetry

### Requirements
- max retrieval loop count: 1 by default
- checkpoint after every major stage
- replayability for eval
- global second-pass quotas
- `degraded_mode: bool` in graph state
- bounded sub-agent depth
- sub-agent spawning disabled in canonical-only mode

### Degraded routes
- **Full mode**: hybrid semantic + graph + policy + decisions; spawn allowed
- **Reduced mode**: semantic + policy + decisions; spawn allowed only for narrow read-only tasks
- **Canonical-only mode**: PostgreSQL policy + structured decisions only; spawn disabled

---

## 7.3 Canonical System-of-Record
**Technology:** PostgreSQL

### Responsibilities
- store structured truth
- store retrieval episodes
- store policy metadata
- store class and cluster metadata
- store online weight updates
- store provenance and answer attribution
- store audit logs and prompt versions
- store agent hierarchy, handoff, lifecycle, and result metadata

### Key tables
- `tenants`
- `users`
- `projects`
- `sessions`
- `conversations`
- `messages`
- `request_log`
- `retrieval_episodes`
- `retrieval_requests`
- `retrieved_items`
- `injected_items`
- `answer_attributions`
- `usefulness_scores`
- `policy_nodes`
- `policy_node_versions`
- `policy_approvals`
- `proto_classes`
- `class_memberships`
- `source_priors`
- `rewrite_template_weights`
- `graph_strategy_weights`
- `blending_weights`
- `prompt_versions`
- `audit_events`
- `eval_runs`
- `agent_instances`
- `agent_memory_links`
- `subagent_results`

### Requirements
- transaction-safe writes
- append-friendly history
- point-in-time auditability
- support for offline replay datasets
- row-level security
- unique `request_id` to guarantee replay/idempotency safety
- all sub-agent records tenant-scoped
- expirable and garbage-collectable runtime child instances

### Additional design requirements
- raw sensitive artifacts stored encrypted at rest
- audit log append-only
- canonical policy activation gated by approval workflow
- lineage preserved without duplicating runtime side effects during replay

#### `agent_instances`
Stores runtime agent instances and hierarchy metadata.

Recommended fields:
- `id`
- `tenant_id`
- `project_id`
- `root_agent_id`
- `parent_agent_id`
- `parent_request_id`
- `task_definition`
- `memory_scope_mode`
- `allowed_sources`
- `depth`
- `status`
- `budget_tokens`
- `created_at`
- `expires_at`
- `completed_at`
- `last_activity_at`
- `cancelled_at`
- `cancellation_reason`

#### `agent_memory_links`
Stores approved handoff links between parent and child execution units.

Recommended fields:
- `id`
- `tenant_id`
- `parent_agent_id`
- `child_agent_id`
- `parent_episode_id`
- `child_episode_id`
- `handoff_type`
- `linked_item_ids`
- `created_at`

#### `subagent_results`
Stores structured child outputs returned to parents.

Recommended fields:
- `id`
- `tenant_id`
- `agent_instance_id`
- `status`
- `summary`
- `evidence_item_ids`
- `artifact_refs`
- `open_questions`
- `created_at`

---

## 7.4 Semantic and Hybrid Retrieval
**Technology:** Qdrant

### Responsibilities
- semantic recall over chunks and memory artifacts
- lexical/hybrid recall for technical terms and code-heavy content
- payload filtering
- low-latency leaf node retrieval

### Indexed objects
- redacted document chunks
- redacted episodic summaries
- semantic facts
- decision records
- issue or event notes
- distilled project state items

### Required payload fields
- `id`
- `tenant_id`
- `project_id`
- `user_id`
- `source_type`
- `node_type`
- `created_at`
- `updated_at`
- `trust_tier`
- `embedding_version`
- `canonical_ref`
- `is_active`
- `sensitivity_tier`
- `redaction_version`

### Requirements
- top-k semantic retrieval
- hybrid search enabled for BM25 + vector
- metadata filtering
- score return for planner and reranker
- batch query support
- mandatory tenant/project filters on every query
- timeout budget per request path
- inheritance-aware access checks when retrieval is executed on behalf of a sub-agent

### Failure handling
- if hybrid search fails, fall back to vector-only
- if Qdrant is unavailable, route to reduced or canonical-only mode

---

## 7.5 Graph Memory
**Technology:** Neo4j

### Responsibilities
- relationship-aware retrieval
- convergence anchor discovery
- shared parent or neighbor analysis
- concept lineage and decision lineage
- agent lineage tracking

### Core node types
- `Tenant`
- `Project`
- `User`
- `Entity`
- `Concept`
- `Message`
- `Summary`
- `Document`
- `Chunk`
- `Decision`
- `Fact`
- `Policy`
- `Workflow`
- `Component`
- `Issue`
- `ProtoClass`
- `AgentInstance`

### Core edge types
- `BELONGS_TO_TENANT`
- `BELONGS_TO_PROJECT`
- `MENTIONS`
- `ABOUT`
- `RELATED_TO`
- `DERIVED_FROM`
- `SUMMARIZES`
- `DECIDED_IN`
- `IMPLEMENTS`
- `USED_IN_ANSWER`
- `RETRIEVED_FOR`
- `BELONGS_TO`
- `SUPPORTS`
- `CONFLICTS_WITH`
- `PARENT_OF`
- `RESULT_FOR`

### Requirements
- support 1 to 2 hop targeted traversals
- support shared-anchor queries
- support confidence on edges
- avoid broad unguided graph expansion
- mandatory tenant/project scoping in traversal
- edge-level `last_retrieved_at` for pruning and freshness management
- lineage edges queryable for replay, eval, and debugging
- user-facing retrieval must not automatically expose lineage graph unless explicitly needed

### Failure handling
- if graph retrieval is unhealthy, skip graph mode and mark `degraded_mode=true`

#### Edge type: `PARENT_OF`
Represents parent-child runtime lineage.

Recommended properties:
- `tenant_id`
- `project_id`
- `handoff_reason`
- `handoff_type`
- `inherited_items`
- `created_at`

#### Edge type: `RESULT_FOR`
Represents child result linkage back to parent or root task.

Recommended properties:
- `tenant_id`
- `project_id`
- `status`
- `created_at`

---

## 7.6 Graph-aware Retrieval
**Technology:** Neo4j GraphRAG

### Responsibilities
- turn graph traversal results into retrieval candidates
- combine graph and semantic evidence
- expose graph neighborhoods as summaries, not raw dumps

### Retrieval modes
- leaf-first convergence
- decision lineage lookup
- concept neighborhood lookup
- component relationship lookup
- conflict or policy resolution lookup

### Requirements
- normalized output contract matching non-graph retrieval
- score harmonization with semantic retrieval
- support bottom-up context assembly
- support explicit blending weights in final scoring

---

## 7.7 Document Ingestion
**Technology:** Unstructured + custom redaction/scrubbing layer

### Responsibilities
- parse uploaded and linked documents
- normalize format differences
- preserve provenance
- emit chunk-ready artifacts
- scrub sensitive data before indexing

### Supported formats
- PDF
- DOCX
- HTML
- Markdown
- TXT

### Requirements
- preserve heading structure
- preserve page and section references
- produce chunk metadata
- support re-chunking without losing canonical doc identity
- sanitize risky content before reinjection
- run mandatory PII/sensitive-data redaction before writing to Qdrant/Neo4j
- allow raw originals only in encrypted storage with retention policy

---

## 7.8 Reranking
**Technology:** Sentence Transformers cross-encoders, plus optional final lightweight LLM reranker

### Responsibilities
- rerank candidate retrieval items
- improve precision before context composition

### Inputs
- user query
- retrieval request
- candidate items
- optional anchor summaries

### Outputs
- reranked candidate list
- calibrated scores
- optional relevance explanation fields

### Requirements
- run only on narrowed candidate sets
- produce stable enough scores for downstream attribution
- support later fine-tuning
- optionally run a final lightweight LLM reranker on top 8 to 10 items for design/tradeoff queries

---

## 7.9 Model Gateway
**Technology:** LiteLLM

### Responsibilities
- standardize model calls
- allow multi-provider routing
- support structured output
- log usage and latency
- expose tokenizer-aware token counting

### Model roles
- answer model: temperature 0.0
- cheap rewriter model: temperature 0.7
- evaluator model: temperature 0.7
- optional critique or classification model: temperature 0.7

### Structured outputs supported
- `CONTEXT_REQUEST`
- `SUBAGENT_SPAWN`
- `SUBAGENT_RESULT`

### Requirements
- retries
- timeouts
- fallback support
- response normalization
- model metadata logging
- tokenizer-aware exact token counting
- prompt version capture in each call record

---

## 7.10 Background Workflow Engine
**Technology:** Temporal

### Responsibilities
- asynchronous ingestion
- re-embedding
- graph construction
- clustering
- replay eval
- batch reweighting
- stale-edge pruning
- runtime agent garbage collection and expiry cleanup

### Requirements
- durable execution
- resumable jobs
- idempotent job design
- strong observability
- separation from online request path

---

## 7.11 Telemetry
**Technology:** OpenTelemetry

### Responsibilities
- trace requests across all layers
- correlate online and offline events
- emit latency and quality metrics
- preserve agent lineage identifiers across parent/child execution

### Trace spans
- request received
- query parsing
- retrieval plan generation
- vector search
- graph traversal
- reranking
- context assembly
- LLM call
- attribution
- feedback write
- sub-agent spawn validation
- sub-agent creation
- inherited context build
- child result ingestion

### Required metrics
- p50 and p95 request latency
- retrieval precision proxy
- context waste ratio
- useful context ratio
- loop rate
- average injected tokens
- answer grounding score
- source usefulness score
- degraded mode rate
- hallucinated constraint rate
- spawn requested rate
- spawn approved rate
- spawn usefulness rate

---

## 7.12 Evals and Observability
**Technology:** Phoenix

### Responsibilities
- evaluate answer quality
- evaluate retrieval usefulness
- support replay experiments
- compare retrieval strategies

### Required eval dimensions
- groundedness
- sufficiency
- precision
- waste
- answer quality
- user correction likelihood
- consistency with policy and canonical memory
- hallucinated constraint detection
- whether a child spawn outperformed direct parent retrieval
- whether a child spawn was actually necessary

### Additional requirements
- support per-item usefulness tagging from `/feedback`
- support side-by-side replay for retrieval-plan variants and prompt versions
- preserve root-agent and child-agent lineage in replay analyses

---

## 8. Online Request Flow

## 8.1 Step 1: Receive query
Input:
```json
{
  "request_id": "r_123",
  "tenant_id": "t_001",
  "project_id": "p_123",
  "session_id": "s_123",
  "user_id": "u_456",
  "message": "Should reconnect state live in the websocket session object or separately?"
}
```

## 8.2 Step 2: Query understanding
Produce query features, not a forced mature taxonomy.

Example:
```json
{
  "features": {
    "is_design_oriented": 0.87,
    "asks_for_tradeoff": 0.82,
    "requires_prior_context": 0.64,
    "component_dense": 0.78,
    "doc_dependency": 0.61,
    "recent_history_dependency": 0.35
  },
  "entities": [
    "websocket session",
    "reconnect state"
  ]
}
```

## 8.3 Step 3: Retrieval plan generation
Generate structured retrieval requests.

Example:
```json
{
  "requests": [
    {
      "source": "decisions",
      "strategy": "leaf_first",
      "query": "prior decisions reconnect state websocket session lifecycle",
      "weight": 0.84
    },
    {
      "source": "docs",
      "strategy": "leaf_first",
      "query": "implementation details websocket session manager reconnect state",
      "weight": 0.79
    },
    {
      "source": "graph",
      "strategy": "convergence_anchor",
      "query": "websocket reconnect state",
      "weight": 0.68
    }
  ]
}
```

## 8.4 Step 4: Plan selection
- rank retrieval requests using source priors, learned weights, estimated token cost, and health status
- use ε-greedy exploration with a small exploration probability, decaying over time
- in exploration mode, permit one lower-weight strategy to run for learning value

## 8.5 Step 5: Retrieval execution
- run hybrid semantic retrieval for leaf candidates
- optionally run graph traversal to find anchors
- pull relevant canonical policy or decision constraints from PostgreSQL
- enforce source-level timeout budgets
- route to degraded mode when dependencies fail

## 8.6 Step 6: Context composition
Build the smallest sufficient context pack.

Rules:
- render anchors before evidence
- deduplicate semantically overlapping evidence
- merge near-duplicates while preserving multiple provenances
- count tokens with the actual tokenizer for the answer model
- apply dynamic budget multipliers based on query features

Example structure:
```json
{
  "policy": [
    "Prefer prior canonical decisions over episodic summaries when conflicts appear."
  ],
  "anchors": [
    {
      "title": "Websocket session lifecycle",
      "summary": "Most relevant retrieved evidence converges on connection lifecycle vs durable recovery state separation."
    }
  ],
  "evidence": [
    {
      "source": "decision",
      "summary": "A prior design note favored separating resumable recovery state from the live transport object."
    },
    {
      "source": "doc_chunk",
      "summary": "Current session manager owns active connection lifecycle, not durable reconnect ownership."
    }
  ]
}
```

## 8.7 Step 7: Initial model call
The LLM receives:
- static constitutional prompt
- compact dynamic context pack
- user message
- protocol for structured context requests and sub-agent spawn requests

## 8.8 Step 8: Optional context request
If needed, the model may return:
```json
{
  "type": "CONTEXT_REQUEST",
  "requests": [
    {
      "source": "recent_history",
      "query": "recent discussion around orphaned websocket sessions",
      "why": "Need current constraints tied to reconnect cleanup concerns",
      "max_items": 3
    }
  ]
}
```

Validation rules:
- reject broad dump requests
- enforce per-user quotas
- enforce allowed source list
- enforce token budget ceilings

## 8.9 Step 9: Optional sub-agent spawn
If the model returns:
```json
{
  "type": "SUBAGENT_SPAWN",
  "task": "Analyze reconnect-state tradeoffs separately from the parent response.",
  "required_memory": ["policy", "decisions", "recent_history", "graph_anchors"],
  "handoff_evidence": ["ri_123", "ri_456"],
  "max_depth": 3,
  "timeout_minutes": 30,
  "memory_scope_mode": "hybrid"
}
```

The broker must:
1. validate tenant, project, and policy scope
2. validate that the task is separable and better served by delegation than retrieval
3. validate depth, active-agent quotas, time budget, and token budget
4. validate `handoff_evidence` against broker-known retrieved items
5. create a new `agent_instance`
6. build the inherited context pack
7. persist lineage and handoff metadata
8. return:
```json
{
  "subagent_handle": "sub_a_789",
  "initial_context_pack": {
    "policy": [],
    "anchors": [],
    "evidence": [],
    "recent_state": []
  },
  "query_url": "/query?agent_id=sub_a_789",
  "expires_at": "2026-04-01T18:00:00Z"
}
```

## 8.10 Step 10: Second pass or delegated child execution
- broker validates the chosen escalation path
- broker retrieves targeted additions for second pass or returns a child handle for delegated execution
- sub-agents use the same `/query` broker flow, but within their scoped runtime boundary

## 8.11 Step 11: Child result ingestion
Child agents return structured results through the broker. Parent agents must explicitly consume or ignore them; they do not implicitly overwrite parent reasoning state.

## 8.12 Step 12: Attribution and persistence
Store:
- what was retrieved
- what was injected
- what likely mattered
- how useful the plan was
- whether the request ran in degraded mode
- prompt version IDs used
- whether spawn was requested, approved, and useful
- lineage identifiers

---

## 9. Prompt Architecture

## 9.1 Static constitutional prompt
Keep this small and stable.

It must define:
- role
- truth ordering
- how retrieved context should be treated
- how conflicts should be surfaced
- context request protocol
- smallest-sufficient-context preference
- sub-agent spawn protocol

Required conflict clause:
> If retrieved items contradict each other, prefer in this order: canonical policy, structured decision records, authoritative document chunks, then everything else. Explicitly note the conflict and state which source you followed.

Required sub-agent clause:
> You may request creation of a specialized sub-agent only for a well-scoped separable sub-task. Use the `SUBAGENT_SPAWN` JSON format. Prefer `CONTEXT_REQUEST` when additional context is sufficient. The broker will decide whether a sub-agent is appropriate, what memory it may receive, and what context is inherited. You remain responsible for the overall task.

### Memory interaction rules
- policy memory overrides all lower-trust memory types
- structured decision memory overrides episodic summaries describing the same decision
- authoritative document chunks outrank generic semantic neighbors
- episodic memory may add recency or nuance but must not silently override policy or decision records
- child agents receive only broker-approved memory
- parent agents remain accountable for integrating child outputs
- sub-agent requests must be minimal and well-scoped

### Prompt versioning
The constitutional prompt and dynamic context template must each have version IDs stored in PostgreSQL and attached to every trace.

## 9.2 Dynamic injected context
Should include:
- applicable policy fragments
- convergence anchors
- supporting evidence
- recent session state if relevant
- provenance where feasible

## 9.3 Forbidden prompt pattern
Do not inject:
- giant raw doc dumps
- raw edge lists by default
- unrelated session history
- broad stale project overviews when not needed

---

## 10. Memory Model

## 10.1 Working memory
Current request/session state.

## 10.2 Episodic memory
Event/history-oriented memory.

## 10.3 Semantic memory
Distilled stable facts.

## 10.4 Decision memory
Accepted tradeoffs, rejected approaches, and rationale.

## 10.5 Document memory
Chunked authoritative content.

## 10.6 Policy memory
Canonical constraints and priority rules.

### Storage policy by memory type
- raw sensitive forms: encrypted storage only
- retrieval indexable forms: redacted summaries/chunks only
- policy/decision records: canonical structured rows plus graph references
- episodic memory: summarized and scrubbed before indexing

### Sub-agent memory rules
- no shared mutable working memory across parent/child boundaries
- inheritance mode must be explicit
- child write-back is mediated through structured results only

---

## 11. Retrieval Strategy Design

## 11.1 Default initial strategy
- retrieve leaf nodes first
- find convergence anchors second
- compose evidence around the anchors

## 11.2 Supported strategies
- direct fact lookup
- direct doc lookup
- leaf-first semantic retrieval
- convergence-anchor graph retrieval
- decision-lineage retrieval
- recent-history lookup
- hybrid blended retrieval

## 11.3 Retrieval scoring dimensions
- semantic similarity
- lexical overlap
- entity overlap
- recency
- trust tier
- source-type prior
- node-type prior
- strategy weight
- context budget cost
- dependency health

## 11.4 Blending formula
The retrieval scorer should support an explicit blended score:
```text
final_score = α·semantic + β·graph + γ·recency + δ·trust_tier + ε·lexical + ζ·cost_penalty
```

These coefficients should live in a learned weights table and be tunable by query family and task signature.

## 11.5 Delegation vs retrieval decision
The planner should record whether:
- additional retrieval likely suffices
- delegation is likely helpful
- delegation was approved
- delegation was actually worth the cost relative to improved retrieval

---

## 12. Query-to-Retrieval Optimization

## 12.1 Purpose
Improve the transformation:
`user query -> retrieval requests`

## 12.2 What gets weighted
- source selection
- rewrite templates
- graph strategy
- recency bias
- node-type preference
- max items / breadth
- semantic vs lexical emphasis
- blending coefficients

## 12.3 Usefulness signals
- answer groundedness
- chunk/reference utilization
- user acceptance
- low confusion follow-up rate
- low context waste
- useful context ratio
- low contradiction rate
- whether a sub-agent outperformed direct retrieval
- whether spawn was necessary

## 12.4 Online update rule
Maintain weights like:
- `source_task_weight`
- `rewrite_template_weight`
- `graph_strategy_weight`
- `blending_weight`

Minimal update:
```text
new_weight = old_weight * (1 - lr) + usefulness_score * lr
```

## 12.5 Exploration policy
- use ε-greedy exploration with ε in the 0.05 to 0.10 range initially
- decay ε over time as confidence increases
- exploration should be bounded to one low-risk alternate retrieval strategy per eligible request

---

## 13. Emergent Taxonomy Design

## 13.1 Bootstrap rule
Do not require a mature classification system at start.

## 13.2 Early representation
Use feature bundles and behavior patterns, not hard labels.

## 13.3 Proto-class model
Each proto-class should store:
- member count
- centroid/embedding
- retrieval signature
- stability score
- label candidates
- promotion status

## 13.4 Clustering inputs
Represent each retrieval episode as a vector composed from:
- query feature bundle
- selected strategies
- source mixture
- usefulness score
- optional answer-shape features
- optional delegation/spawn behavior

## 13.5 Clustering job
- run HDBSCAN or similar density-based clustering in a Temporal background job
- recompute periodically
- preserve lineage between prior and new clusters

## 13.6 Promotion criteria
A proto-class becomes operational only if it:
- has at least 30 members
- maintains stability score >= 0.75 over a 7-day window
- predicts useful retrieval behavior better than baseline routing

## 13.7 Merge/split behavior
- merge classes with similar retrieval signatures and overlapping members
- split classes whose usefulness varies strongly by sub-pattern
- allow alias names
- provide admin overrides for force-merge, force-split, and manual promotion

---

## 14. Data Contracts

## 14.1 Retrieval request
```json
{
  "source": "docs|memory|decisions|graph|recent_history|policy",
  "strategy": "direct|leaf_first|convergence_anchor|decision_lineage|hybrid",
  "query": "string",
  "weight": 0.0,
  "constraints": {
    "max_items": 5,
    "prefer_recent": true,
    "trust_min": 0.6,
    "timeout_ms": 800
  }
}
```

## 14.2 Retrieved item
```json
{
  "item_id": "ri_123",
  "tenant_id": "t_001",
  "project_id": "p_123",
  "source": "docs",
  "node_type": "chunk",
  "score": 0.83,
  "summary": "string",
  "provenance": {
    "doc_id": "d_1",
    "section": "3.2",
    "page": 7
  }
}
```

## 14.3 Context pack
```json
{
  "policy": [],
  "anchors": [],
  "evidence": [],
  "recent_state": [],
  "budget": {
    "input_tokens": 1200,
    "actual_tokenizer": "model-specific"
  }
}
```

## 14.4 Context request
```json
{
  "type": "CONTEXT_REQUEST",
  "requests": [
    {
      "source": "recent_history",
      "query": "string",
      "why": "string",
      "max_items": 3
    }
  ]
}
```

## 14.5 Retrieval episode
```json
{
  "episode_id": "ep_123",
  "request_id": "r_123",
  "query": "string",
  "features": {},
  "retrieval_requests": [],
  "retrieved_items": [],
  "injected_items": [],
  "answer_summary": "string",
  "usefulness_score": 0.74,
  "degraded_mode": false
}
```

## 14.6 Sub-agent spawn request
```json
{
  "type": "SUBAGENT_SPAWN",
  "task": "string",
  "required_memory": ["policy", "decisions", "recent_history", "graph_anchors"],
  "handoff_evidence": ["ri_123", "ri_456"],
  "max_depth": 3,
  "timeout_minutes": 30,
  "memory_scope_mode": "copy_in|reference_link|hybrid"
}
```

### Validation rules
- `task` must be explicit and bounded
- `required_memory` must use allowed source classes only
- `handoff_evidence` must reference broker-known, tenant-valid items
- `max_depth` may not exceed broker policy
- `memory_scope_mode` defaults to `hybrid` if omitted

## 14.7 Sub-agent result
```json
{
  "type": "SUBAGENT_RESULT",
  "subagent_handle": "sub_a_789",
  "status": "completed",
  "summary": "Separate reconnect state from the live transport object.",
  "evidence": ["ri_123", "ri_456"],
  "artifacts": [],
  "open_questions": []
}
```

### Result rules
- child output must be structured
- evidence must refer to broker-known items
- result ingestion must be auditable
- parent must explicitly consume or ignore child output; no implicit overwrite of parent reasoning state

---

## 15. Context Budget Rules

### Hard rules
- keep policy separate from retrieved evidence
- dedupe semantically overlapping evidence
- prefer 2 to 5 strong evidence items over 15 mediocre ones
- anchors should explain grouping, not replace evidence
- render anchors before evidence
- recent state only if it materially changes the answer
- second-pass added context must be smaller than first-pass context by default
- count tokens using the exact tokenizer for the answer model

### Suggested budget allocation
Base split:
- 15% policy
- 20% anchor summaries
- 45% evidence
- 20% recent state / supplemental context

Dynamic multipliers:
- `is_design_oriented=true` → +10% anchor budget
- `doc_dependency high` → +10% evidence budget
- `recent_history_dependency high` → +10% recent-state budget

---

## 16. Trust and Precedence Model

When conflicts appear:

1. canonical policy
2. canonical structured facts
3. stable decision memory
4. authoritative documents
5. recent episodic summaries
6. generic semantic neighbors

The LLM should be told this order explicitly. The same ordering applies to child-agent context packs.

---

## 17. Observability Requirements

Every online request must be traceable through:
- retrieval plan chosen
- candidate items returned
- reranker decisions
- final injected context
- model outputs
- optional context requests
- feedback outcome
- sub-agent lineage where applicable

Required dashboards:
- retrieval precision trend
- context waste trend
- useful context ratio trend
- loop invocation rate
- degraded mode rate
- p95 latency by stage
- usefulness by source type
- usefulness by rewrite template
- class stability over time
- hallucinated constraint rate
- spawn requested vs approved trend
- spawn usefulness trend

---

## 18. API Schema Plan

### `POST /query`
Request:
```json
{
  "request_id": "r_123",
  "tenant_id": "t_001",
  "project_id": "p_123",
  "session_id": "s_123",
  "user_id": "u_456",
  "message": "string",
  "stream": true,
  "agent_id": "optional_subagent_handle"
}
```

Response:
```json
{
  "request_id": "r_123",
  "answer": "string",
  "degraded_mode": false,
  "trace_id": "trace_abc",
  "prompt_version_id": "pv_001",
  "context_template_version_id": "ctv_001"
}
```

### `POST /feedback`
Request:
```json
{
  "request_id": "r_123",
  "tenant_id": "t_001",
  "user_id": "u_456",
  "accepted": true,
  "score": 0.9,
  "retrieved_item_ids": ["ri_1", "ri_2"],
  "notes": "Decision record was especially useful."
}
```

### `POST /replay`
Request:
```json
{
  "tenant_id": "t_001",
  "episode_ids": ["ep_1", "ep_2"],
  "candidate_strategies": ["baseline", "hybrid_v2"]
}
```

---

## 19. Pydantic Model Plan

Core models:
- `BrokerQueryRequest`
- `BrokerQueryResponse`
- `QueryFeatures`
- `RetrievalRequest`
- `RetrievedItem`
- `ContextPack`
- `ContextRequest`
- `RetrievalEpisode`
- `FeedbackRequest`
- `ProtoClassAdminAction`
- `SubagentSpawnRequest`
- `SubagentResult`

All models must include tenant-aware fields where relevant.

---

## 20. PostgreSQL Schema Plan

Key additions beyond base schema:
- `request_log.request_id UNIQUE`
- `prompt_versions(id, type, version, content, is_active)`
- `audit_events(id, tenant_id, actor_id, action, target_type, target_id, reason, created_at)`
- `policy_nodes(approval_status, owner_id, approver_id, effective_from, effective_to)`
- row-level security policies on tenant-owned tables
- encrypted blobs for raw sensitive artifacts

### `agent_instances`
```sql
create table agent_instances (
  id uuid primary key,
  tenant_id text not null,
  project_id text not null,
  root_agent_id uuid references agent_instances(id),
  parent_agent_id uuid references agent_instances(id),
  parent_request_id text,
  task_definition text not null,
  memory_scope_mode text not null default 'hybrid',
  allowed_sources jsonb not null default '[]'::jsonb,
  depth int not null default 0,
  status text not null default 'active',
  budget_tokens int,
  created_at timestamptz not null default now(),
  expires_at timestamptz,
  completed_at timestamptz,
  last_activity_at timestamptz,
  cancelled_at timestamptz,
  cancellation_reason text
);
```

### `agent_memory_links`
```sql
create table agent_memory_links (
  id uuid primary key,
  tenant_id text not null,
  parent_agent_id uuid not null references agent_instances(id),
  child_agent_id uuid not null references agent_instances(id),
  parent_episode_id uuid,
  child_episode_id uuid,
  handoff_type text not null,
  linked_item_ids jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default now()
);
```

### `subagent_results`
```sql
create table subagent_results (
  id uuid primary key,
  tenant_id text not null,
  agent_instance_id uuid not null references agent_instances(id),
  status text not null,
  summary text not null,
  evidence_item_ids jsonb not null default '[]'::jsonb,
  artifact_refs jsonb not null default '[]'::jsonb,
  open_questions jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default now()
);
```

---

## 21. Neo4j Schema Plan

Required properties:
- every tenant-owned node carries `tenant_id`, `project_id`
- every edge carries `tenant_id`
- retrievable edges carry `last_retrieved_at`, `confidence`

Useful indexes:
- `(tenant_id, project_id, node_type)`
- `(tenant_id, canonical_ref)`
- `(tenant_id, name)` for entities/concepts
- `(tenant_id, agent_id)` for runtime agent nodes where applicable

---

## 22. LangGraph Node Plan

Suggested nodes:
1. `validate_request`
2. `enforce_auth_and_budget`
3. `extract_features`
4. `build_candidate_retrieval_plan`
5. `check_dependency_health`
6. `select_execution_mode`
7. `run_semantic_retrieval`
8. `run_graph_retrieval`
9. `fetch_canonical_policy`
10. `fetch_structured_decisions`
11. `rerank_candidates`
12. `compose_context_pack`
13. `count_exact_tokens`
14. `call_answer_model`
15. `inspect_for_context_request`
16. `inspect_for_subagent_spawn`
17. `validate_context_request`
18. `validate_subagent_spawn`
19. `run_second_pass_retrieval`
20. `compose_second_pass_context`
21. `create_subagent_instance`
22. `build_inherited_context_pack`
23. `persist_agent_lineage`
24. `call_second_pass_model`
25. `consume_subagent_result`
26. `attribute_answer`
27. `persist_episode`
28. `emit_traces_and_metrics`
29. `garbage_collect_subagent`

State fields:
- `request_id`
- `tenant_id`
- `project_id`
- `query_features`
- `retrieval_plan`
- `retrieved_items`
- `injected_items`
- `degraded_mode`
- `prompt_version_id`
- `context_template_version_id`
- `health_status`
- `agent_id`
- `root_agent_id`
- `parent_agent_id`
- `agent_depth`
- `subagent_spawn_requested`
- `subagent_spawn_approved`
- `memory_scope_mode`
- `allowed_sources`
- `expires_at`

---

## 23. Failure and Recovery Requirements

### Dependency failures
- Qdrant unhealthy → skip semantic/hybrid retrieval, continue in reduced/canonical mode
- Neo4j unhealthy → skip graph retrieval, continue without anchors or use previously cached anchors
- LiteLLM provider unhealthy → fail over to configured alternate model/provider
- tokenizer failure → fail closed on prompt assembly, do not exceed guessed budget

### Recovery expectations
- all degraded runs logged explicitly
- no cross-tenant leakage in fallback modes
- replay jobs must be side-effect safe due to `request_id` uniqueness
- sub-agent instances must expire or be cancellable
- parent cancellation should prevent orphaned unlimited child execution

---

## 24. MVP and V1 Scope

## Required for MVP
- FastAPI
- LangGraph
- PostgreSQL
- LiteLLM
- Unstructured
- Qdrant
- cross-encoder reranking
- OpenTelemetry
- Phoenix
- tenant isolation enforcement
- exact token budgeting

## Strongly recommended for V1
- Neo4j
- GraphRAG
- retrieval weight tuning
- proto-class storage
- degraded-mode routing
- prompt versioning
- audit logging
- sub-agent spawn support via structured output
- runtime instance creation and expiry
- agent lineage tracking in PostgreSQL and Neo4j
- structured child result ingestion

## Can wait until V2
- Temporal
- fully automated merge/split taxonomy
- local model serving with vLLM
- lightweight final LLM reranker everywhere
- advanced sub-agent coordination primitives
- sibling coordination
- shared result aggregation tools
- persistent role-specialized agent families

---

## 25. Suggested Implementation Phases

## Phase 1: functional broker
- build FastAPI broker
- add LangGraph flow
- add LiteLLM
- add request IDs, auth, quotas, and rate limiting
- store retrieval episodes in PostgreSQL

## Phase 2: secure semantic memory
- ingest docs with Unstructured
- add redaction pipeline
- embed and index in Qdrant
- implement hybrid search and reranking
- build initial context composer with exact token counting

## Phase 3: learning loop
- log usefulness signals
- add retrieval weight tuning
- add ε-greedy exploration
- add replay evals in Phoenix

## Phase 4: graph memory
- add Neo4j
- add leaf-first + convergence-anchor retrieval
- blend graph and semantic evidence
- add stale-edge pruning

## Phase 5: emergent taxonomy
- cluster retrieval episodes with HDBSCAN
- create proto-classes
- use stable classes to improve routing
- add admin override workflow

## Phase 6: bounded multi-agent support
- add structured `SUBAGENT_SPAWN`
- add runtime agent instance tables and lifecycle
- add inherited context pack builder
- add lineage tracking and child result ingestion
- add expiry and cleanup

---

## 26. One-Line Operational Summary

This system should behave like:

**a tenant-safe, hierarchical brokered memory-and-context engine that injects the smallest sufficient grounded context before any model call, allows one structured escalation for more context or the creation of a new runtime sub-agent with inherited broker-governed memory, degrades safely when dependencies fail, and gets better over time by learning which retrieval plans actually help across entire agent hierarchies.**
