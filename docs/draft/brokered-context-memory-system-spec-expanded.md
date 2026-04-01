# Brokered Context Memory System
## Reference Architecture Specification

## 1. Purpose

This system replaces static runtime context files with a **brokered context engine** that:

- interprets a user request
- builds the smallest sufficient initial context pack
- calls the LLM once with that context
- allows the LLM to request additional context in a structured way
- learns over time which retrieval plans are useful
- develops an emergent classification system from usage rather than requiring a perfect taxonomy on day one

---

## 2. Primary Goals

### Functional goals
- inject relevant context before the first LLM call
- support structured follow-up context requests
- unify memory, docs, decisions, policy, and recent history
- support graph-aware retrieval and bottom-up convergence
- continuously improve query-to-retrieval planning

### Quality goals
- low latency on the happy path
- bounded retrieval loops
- high provenance and auditability
- low context waste
- graceful operation from zero or near-zero prior memory
- progressive self-organization into useful classes

---

## 3. Non-goals

- fully autonomous open-ended agent behavior
- unrestricted model access to storage internals
- dumping raw graph neighborhoods into prompts by default
- replacing all canonical human-authored policy with emergent memory

---

## 4. System Overview

```text
User Query
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
   |      +--> Semantic Search (Qdrant)
   |      +--> Graph Search (Neo4j / GraphRAG)
   |      +--> Canonical Metadata (PostgreSQL)
   |      +--> Documents (Unstructured outputs)
   |
   +--> Context Composer / Budgeter
   |
   +--> LLM Gateway (LiteLLM)
   |
   +--> Optional Context Request Loop
   |
   +--> Final Answer
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
Initial retrieval should be selective, ranked, budgeted, and explainable.

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

---

## 6. Major Components

## 6.1 Broker API
**Technology:** FastAPI

### Responsibilities
- receive user requests
- validate schemas
- invoke orchestration flow
- expose sync and streaming endpoints
- surface trace IDs and debug info when needed

### Endpoints
- `POST /query`
- `POST /feedback`
- `POST /replay`
- `GET /health`
- `GET /trace/{id}`

### Requirements
- typed request and response contracts
- auth support
- idempotency support
- trace propagation
- streaming completion support

---

## 6.2 Execution Graph
**Technology:** LangGraph

### Responsibilities
- coordinate all online steps
- persist checkpoints
- support bounded loop behavior
- support deterministic retries

### Online flow
1. parse request
2. extract query features
3. generate retrieval plan candidates
4. execute retrieval
5. compose initial context pack
6. call LLM
7. inspect result
8. if `CONTEXT_REQUEST`, retrieve more and run second pass
9. finalize answer
10. persist episode and telemetry

### Requirements
- max retrieval loop count: 1 by default
- checkpoint after every major stage
- replayability for eval

---

## 6.3 Canonical System-of-Record
**Technology:** PostgreSQL

### Responsibilities
- store structured truth
- store retrieval episodes
- store policy metadata
- store class and cluster metadata
- store online weight updates
- store provenance and answer attribution

### Key tables
- `users`
- `sessions`
- `conversations`
- `messages`
- `retrieval_episodes`
- `retrieval_requests`
- `retrieved_items`
- `injected_items`
- `answer_attributions`
- `usefulness_scores`
- `policy_nodes`
- `proto_classes`
- `class_memberships`
- `source_priors`
- `rewrite_template_weights`
- `graph_strategy_weights`
- `eval_runs`

### Requirements
- transaction-safe writes
- append-friendly history
- point-in-time auditability
- support for offline replay datasets

---

## 6.4 Semantic Retrieval
**Technology:** Qdrant

### Responsibilities
- semantic recall over chunks and memory artifacts
- payload filtering
- low-latency leaf node retrieval

### Indexed objects
- document chunks
- episodic summaries
- semantic facts
- decision records
- issue or event notes
- distilled project state items

### Required payload fields
- `id`
- `source_type`
- `node_type`
- `project_id`
- `user_id`
- `created_at`
- `updated_at`
- `trust_tier`
- `embedding_version`
- `canonical_ref`
- `is_active`

### Requirements
- top-k semantic retrieval
- metadata filtering
- score return for planner and reranker
- batch query support

---

## 6.5 Graph Memory
**Technology:** Neo4j

### Responsibilities
- relationship-aware retrieval
- convergence anchor discovery
- shared parent or neighbor analysis
- concept lineage and decision lineage

### Core node types
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

### Core edge types
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

### Requirements
- support 1 to 2 hop targeted traversals
- support shared-anchor queries
- support confidence on edges
- avoid broad unguided graph expansion

---

## 6.6 Graph-aware Retrieval
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

---

## 6.7 Document Ingestion
**Technology:** Unstructured

### Responsibilities
- parse uploaded and linked documents
- normalize format differences
- preserve provenance
- emit chunk-ready artifacts

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

---

## 6.8 Reranking
**Technology:** Sentence Transformers cross-encoders

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

---

## 6.9 Model Gateway
**Technology:** LiteLLM

### Responsibilities
- standardize model calls
- allow multi-provider routing
- support structured output
- log usage and latency

### Model roles
- answer model
- cheap rewriter model
- evaluator model
- optional critique or classification model

### Requirements
- retries
- timeouts
- fallback support
- response normalization
- model metadata logging

---

## 6.10 Background Workflow Engine
**Technology:** Temporal

### Responsibilities
- asynchronous ingestion
- re-embedding
- graph construction
- clustering
- replay eval
- batch reweighting

### Requirements
- durable execution
- resumable jobs
- idempotent job design
- strong observability
- separation from online request path

---

## 6.11 Telemetry
**Technology:** OpenTelemetry

### Responsibilities
- trace requests across all layers
- correlate online and offline events
- emit latency and quality metrics

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

### Required metrics
- p50 and p95 request latency
- retrieval precision proxy
- context waste ratio
- loop rate
- average injected tokens
- answer grounding score
- source usefulness score

---

## 6.12 Evals and Observability
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

---

## 7. Online Request Flow

## 7.1 Step 1: Receive query
Input:
```json
{
  "session_id": "s_123",
  "user_id": "u_456",
  "message": "Should reconnect state live in the websocket session object or separately?"
}
```

## 7.2 Step 2: Query understanding
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

## 7.3 Step 3: Retrieval plan generation
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

## 7.4 Step 4: Retrieval execution
- run vector retrieval for leaf candidates
- optionally run graph traversal to find anchors
- pull relevant canonical policy or decision constraints from PostgreSQL

## 7.5 Step 5: Context composition
Build smallest sufficient context pack.

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

## 7.6 Step 6: Initial model call
The LLM receives:
- core system prompt
- compact context pack
- user message
- protocol for structured context requests

## 7.7 Step 7: Optional context request
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

## 7.8 Step 8: Second pass
Broker validates request, retrieves targeted additions, and performs one more call.

## 7.9 Step 9: Attribution and persistence
Store:
- what was retrieved
- what was injected
- what likely mattered
- how useful the plan was

---

## 8. Prompt Architecture

## 8.1 Static constitutional prompt
Keep this small and stable.

Example responsibilities:
- define role
- define truth ordering
- define how retrieved context should be treated
- define context request protocol

Example principles:
- canonical policy > stable decisions > episodic summaries
- do not invent unseen context
- ask for more context only through structured JSON
- prefer smallest sufficient request

## 8.2 Dynamic injected context
Should include:
- applicable policy fragments
- convergence anchors
- supporting evidence
- recent session state if relevant
- provenance where feasible

## 8.3 Forbidden prompt pattern
Do not inject:
- giant raw doc dumps
- raw edge lists by default
- unrelated session history
- broad stale project overviews when not needed

---

## 9. Memory Model

## 9.1 Working memory
Current request and session state.

## 9.2 Episodic memory
Event and history-oriented memory.

## 9.3 Semantic memory
Distilled stable facts.

## 9.4 Decision memory
Accepted tradeoffs and rationale summaries.

## 9.5 Document memory
Chunked authoritative content.

## 9.6 Policy memory
Canonical constraints and priority rules.

---

## 10. Retrieval Strategy Design

## 10.1 Default initial strategy
- retrieve leaf nodes first
- find convergence anchors second
- compose evidence around the anchors

## 10.2 Supported strategies
- direct fact lookup
- direct doc lookup
- leaf-first semantic retrieval
- convergence-anchor graph retrieval
- decision-lineage retrieval
- recent-history lookup
- hybrid blended retrieval

## 10.3 Retrieval scoring dimensions
- semantic similarity
- lexical overlap
- entity overlap
- recency
- trust tier
- source-type prior
- node-type prior
- strategy weight
- context budget cost

---

## 11. Query-to-Retrieval Optimization

## 11.1 Purpose
Improve the transformation from user query to retrieval requests.

## 11.2 What gets weighted
- source selection
- rewrite templates
- graph strategy
- recency bias
- node-type preference
- max items and breadth
- semantic vs lexical emphasis

## 11.3 Usefulness signals
- answer groundedness
- chunk and reference utilization
- user acceptance
- low confusion follow-up rate
- low context waste
- low contradiction rate

## 11.4 Minimal update rule
Maintain weights like:
- `source_task_weight`
- `rewrite_template_weight`
- `graph_strategy_weight`

Online update:
```text
new_weight = old_weight * (1 - lr) + usefulness_score * lr
```

---

## 12. Emergent Taxonomy Design

## 12.1 Bootstrap rule
Do not require a mature classification system at start.

## 12.2 Early representation
Use feature bundles and behavior patterns, not hard labels.

## 12.3 Proto-class model
Each proto-class should store:
- member count
- centroid or embedding
- retrieval signature
- stability score
- label candidates
- promotion status

## 12.4 Promotion criteria
A proto-class becomes operational only if it:
- appears often enough
- has coherent membership
- predicts useful retrieval behavior
- remains stable over time

## 12.5 Merge and split behavior
- merge classes with similar retrieval signatures and overlapping members
- split classes whose usefulness varies strongly by sub-pattern
- allow alias names

---

## 13. Data Contracts

## 13.1 Retrieval request
```json
{
  "source": "docs|memory|decisions|graph|recent_history|policy",
  "strategy": "direct|leaf_first|convergence_anchor|decision_lineage|hybrid",
  "query": "string",
  "weight": 0.0,
  "constraints": {
    "max_items": 5,
    "prefer_recent": true,
    "trust_min": 0.6
  }
}
```

## 13.2 Retrieved item
```json
{
  "item_id": "ri_123",
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

## 13.3 Context pack
```json
{
  "policy": [],
  "anchors": [],
  "evidence": [],
  "recent_state": [],
  "budget": {
    "input_tokens": 1200
  }
}
```

## 13.4 Context request
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

## 13.5 Retrieval episode
```json
{
  "episode_id": "ep_123",
  "query": "string",
  "features": {},
  "retrieval_requests": [],
  "retrieved_items": [],
  "injected_items": [],
  "answer_summary": "string",
  "usefulness_score": 0.74
}
```

---

## 14. Context Budget Rules

### Hard rules
- keep policy separate from retrieved evidence
- dedupe semantically overlapping evidence
- prefer 2 to 5 strong evidence items over 15 mediocre ones
- anchors should explain grouping, not replace evidence
- recent state only if it materially changes the answer
- second-pass added context must be smaller than first-pass context by default

### Suggested budget allocation
- 15% policy
- 20% anchor summaries
- 45% evidence
- 20% recent state or supplemental context

Adjust by task type.

---

## 15. Trust and Precedence Model

When conflicts appear:
1. canonical policy
2. canonical structured facts
3. stable decision memory
4. authoritative documents
5. recent episodic summaries
6. generic semantic neighbors

The LLM should be told this order explicitly.

---

## 16. Observability Requirements

Every online request must be traceable through:
- retrieval plan chosen
- candidate items returned
- reranker decisions
- final injected context
- model outputs
- optional context requests
- feedback outcome

Required dashboards:
- retrieval precision trend
- context waste trend
- loop invocation rate
- p95 latency by stage
- usefulness by source type
- usefulness by rewrite template
- class stability over time

---

## 17. MVP Scope

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

## Strongly recommended for V1
- Neo4j
- GraphRAG
- retrieval weight tuning
- proto-class storage

## Can wait until V2
- Temporal
- fully automated merge and split taxonomy
- local model serving with vLLM
- advanced graph neighborhood request tools

---

## 18. Suggested Implementation Phases

## Phase 1: functional broker
- build FastAPI broker
- add LangGraph flow
- add LiteLLM
- store retrieval episodes in PostgreSQL

## Phase 2: semantic memory
- ingest docs with Unstructured
- embed and index in Qdrant
- implement reranking
- build initial context composer

## Phase 3: learning loop
- log usefulness signals
- add retrieval weight tuning
- add replay evals in Phoenix

## Phase 4: graph memory
- add Neo4j
- add leaf-first and convergence-anchor retrieval
- blend graph and semantic evidence

## Phase 5: emergent taxonomy
- cluster retrieval episodes
- create proto-classes
- use stable classes to improve routing

---

## 19. API Schema Specification

## 19.1 POST /query
### Request schema
```json
{
  "request_id": "optional-string",
  "session_id": "string",
  "user_id": "string",
  "message": "string",
  "conversation_id": "optional-string",
  "project_id": "optional-string",
  "stream": true,
  "debug": false,
  "constraints": {
    "max_retrieval_loops": 1,
    "max_context_tokens": 2400,
    "allow_graph": true,
    "allow_recent_history": true
  }
}
```

### Response schema
```json
{
  "request_id": "string",
  "trace_id": "string",
  "answer": "string",
  "used_second_pass": false,
  "context_summary": {
    "anchors_used": 1,
    "evidence_used": 3,
    "policy_fragments_used": 1
  },
  "debug": {
    "retrieval_episode_id": "optional-string",
    "selected_strategy": "optional-string"
  }
}
```

## 19.2 POST /feedback
### Request schema
```json
{
  "request_id": "string",
  "user_id": "string",
  "rating": 1,
  "accepted": true,
  "comment": "optional-string",
  "issue_type": "optional-string"
}
```

### Response schema
```json
{
  "status": "ok",
  "feedback_id": "string"
}
```

## 19.3 POST /replay
### Request schema
```json
{
  "eval_run_id": "string",
  "episode_ids": ["ep_1", "ep_2"],
  "variant": {
    "rewrite_template_version": "v2",
    "graph_strategy": "convergence_anchor",
    "max_items": 4
  }
}
```

### Response schema
```json
{
  "status": "queued",
  "eval_run_id": "string"
}
```

---

## 20. Pydantic Model Plan

```python
from pydantic import BaseModel, Field
from typing import Any, Literal

class QueryConstraints(BaseModel):
    max_retrieval_loops: int = 1
    max_context_tokens: int = 2400
    allow_graph: bool = True
    allow_recent_history: bool = True

class QueryRequest(BaseModel):
    request_id: str | None = None
    session_id: str
    user_id: str
    message: str
    conversation_id: str | None = None
    project_id: str | None = None
    stream: bool = True
    debug: bool = False
    constraints: QueryConstraints = Field(default_factory=QueryConstraints)

class RetrievalConstraints(BaseModel):
    max_items: int = 5
    prefer_recent: bool = True
    trust_min: float = 0.6

class RetrievalRequest(BaseModel):
    source: Literal["docs", "memory", "decisions", "graph", "recent_history", "policy"]
    strategy: Literal["direct", "leaf_first", "convergence_anchor", "decision_lineage", "hybrid"]
    query: str
    weight: float = 0.0
    constraints: RetrievalConstraints = Field(default_factory=RetrievalConstraints)

class Provenance(BaseModel):
    doc_id: str | None = None
    section: str | None = None
    page: int | None = None
    canonical_ref: str | None = None

class RetrievedItem(BaseModel):
    item_id: str
    source: str
    node_type: str
    score: float
    summary: str
    provenance: Provenance = Field(default_factory=Provenance)
    metadata: dict[str, Any] = Field(default_factory=dict)

class Anchor(BaseModel):
    title: str
    summary: str
    score: float | None = None

class ContextPack(BaseModel):
    policy: list[str] = Field(default_factory=list)
    anchors: list[Anchor] = Field(default_factory=list)
    evidence: list[RetrievedItem] = Field(default_factory=list)
    recent_state: list[str] = Field(default_factory=list)
    budget: dict[str, Any] = Field(default_factory=dict)

class ContextRequestItem(BaseModel):
    source: Literal["memory", "docs", "decisions", "graph", "recent_history", "policy"]
    query: str
    why: str
    max_items: int = 3

class ContextRequest(BaseModel):
    type: Literal["CONTEXT_REQUEST"]
    requests: list[ContextRequestItem]
```

---

## 21. PostgreSQL Schema Plan

## 21.1 Core online tables

### `retrieval_episodes`
```sql
create table retrieval_episodes (
  id uuid primary key,
  request_id text unique not null,
  user_id text not null,
  session_id text not null,
  conversation_id text,
  project_id text,
  raw_query text not null,
  query_features jsonb not null default '{}'::jsonb,
  selected_strategy text,
  used_second_pass boolean not null default false,
  usefulness_score numeric,
  answer_summary text,
  trace_id text,
  created_at timestamptz not null default now()
);
```

### `retrieval_requests`
```sql
create table retrieval_requests (
  id uuid primary key,
  retrieval_episode_id uuid not null references retrieval_episodes(id) on delete cascade,
  source text not null,
  strategy text not null,
  query_text text not null,
  request_weight numeric,
  constraints jsonb not null default '{}'::jsonb,
  ordinal int not null,
  created_at timestamptz not null default now()
);
```

### `retrieved_items`
```sql
create table retrieved_items (
  id uuid primary key,
  retrieval_episode_id uuid not null references retrieval_episodes(id) on delete cascade,
  retrieval_request_id uuid references retrieval_requests(id) on delete set null,
  item_id text not null,
  source text not null,
  node_type text not null,
  retrieval_score numeric,
  rerank_score numeric,
  injected boolean not null default false,
  provenance jsonb not null default '{}'::jsonb,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
```

### `answer_attributions`
```sql
create table answer_attributions (
  id uuid primary key,
  retrieval_episode_id uuid not null references retrieval_episodes(id) on delete cascade,
  retrieved_item_id uuid not null references retrieved_items(id) on delete cascade,
  attribution_score numeric not null,
  attribution_method text not null,
  created_at timestamptz not null default now()
);
```

### `usefulness_scores`
```sql
create table usefulness_scores (
  id uuid primary key,
  retrieval_episode_id uuid not null references retrieval_episodes(id) on delete cascade,
  groundedness_score numeric,
  sufficiency_score numeric,
  precision_score numeric,
  waste_score numeric,
  user_acceptance_score numeric,
  contradiction_score numeric,
  total_score numeric,
  created_at timestamptz not null default now()
);
```

## 21.2 Optimization tables

### `source_priors`
```sql
create table source_priors (
  id uuid primary key,
  task_signature text not null,
  source text not null,
  weight numeric not null,
  sample_count int not null default 0,
  updated_at timestamptz not null default now(),
  unique (task_signature, source)
);
```

### `rewrite_template_weights`
```sql
create table rewrite_template_weights (
  id uuid primary key,
  task_signature text not null,
  template_name text not null,
  weight numeric not null,
  sample_count int not null default 0,
  updated_at timestamptz not null default now(),
  unique (task_signature, template_name)
);
```

### `graph_strategy_weights`
```sql
create table graph_strategy_weights (
  id uuid primary key,
  task_signature text not null,
  graph_strategy text not null,
  weight numeric not null,
  sample_count int not null default 0,
  updated_at timestamptz not null default now(),
  unique (task_signature, graph_strategy)
);
```

## 21.3 Taxonomy tables

### `proto_classes`
```sql
create table proto_classes (
  id uuid primary key,
  stable_name text,
  label_candidates jsonb not null default '[]'::jsonb,
  centroid_ref text,
  retrieval_signature jsonb not null default '{}'::jsonb,
  stability_score numeric not null default 0,
  member_count int not null default 0,
  status text not null default 'candidate',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
```

### `class_memberships`
```sql
create table class_memberships (
  id uuid primary key,
  proto_class_id uuid not null references proto_classes(id) on delete cascade,
  retrieval_episode_id uuid not null references retrieval_episodes(id) on delete cascade,
  membership_score numeric not null,
  created_at timestamptz not null default now(),
  unique (proto_class_id, retrieval_episode_id)
);
```

---

## 22. Neo4j Schema Plan

## 22.1 Node labels
- `Entity {id, name, entity_type, confidence}`
- `Concept {id, name, scope, confidence}`
- `Document {id, title, source_type, trust_tier}`
- `Chunk {id, chunk_index, summary, canonical_ref}`
- `Decision {id, title, status, trust_tier}`
- `Summary {id, summary_type, created_at}`
- `Policy {id, title, priority, canonical}`
- `Component {id, name, system, confidence}`
- `Issue {id, title, severity, created_at}`
- `ProtoClass {id, stable_name, stability_score}`

## 22.2 Relationship properties
All relationships should support, where relevant:
- `confidence`
- `created_at`
- `updated_at`
- `source_ref`
- `active`

## 22.3 Required traversal patterns
- leaf chunk -> concept -> decision
- decision -> component -> related issue
- summary -> mentions entity -> about concept
- chunk -> belongs_to document -> supports decision
- retrieved item set -> shared concept anchors

---

## 23. LangGraph Node Plan

## 23.1 State object
```python
class BrokerState(TypedDict, total=False):
    request_id: str
    user_id: str
    session_id: str
    conversation_id: str | None
    project_id: str | None
    message: str
    query_features: dict[str, float]
    entities: list[str]
    retrieval_plan: list[dict]
    retrieved_items: list[dict]
    anchors: list[dict]
    context_pack: dict
    llm_output: str
    context_request: dict | None
    second_pass_items: list[dict]
    final_answer: str
    retrieval_episode_id: str
    trace_id: str
    debug: dict
```

## 23.2 Nodes

### `normalize_request`
**Input:** raw API request  
**Output:** normalized broker state  
**Responsibilities:** validate defaults, stamp request id, attach trace id.

### `extract_query_features`
**Input:** normalized state  
**Output:** query features and entity list  
**Responsibilities:** infer weak task signals, extract entities, detect ambiguity.

### `build_candidate_retrieval_plan`
**Input:** query features and entities  
**Output:** candidate retrieval requests  
**Responsibilities:** choose sources, rewrite queries, assign initial weights.

### `score_and_select_plan`
**Input:** candidate plan  
**Output:** selected plan subset  
**Responsibilities:** apply priors, budget constraints, task compatibility, historical weights.

### `retrieve_semantic_leaves`
**Input:** selected plan  
**Output:** semantic candidates from Qdrant  
**Responsibilities:** vector lookup for leaf nodes.

### `retrieve_graph_anchors`
**Input:** selected plan and semantic candidates  
**Output:** graph anchors and graph-derived candidates  
**Responsibilities:** convergence-anchor discovery, decision lineage, neighborhood summarization.

### `retrieve_policy_and_canonical`
**Input:** query features and entities  
**Output:** policy fragments and canonical constraints  
**Responsibilities:** enforce trust precedence and policy retrieval.

### `rerank_candidates`
**Input:** all candidates  
**Output:** reranked candidates  
**Responsibilities:** improve precision across sources.

### `compose_context_pack`
**Input:** reranked candidates, anchors, policy  
**Output:** context pack  
**Responsibilities:** dedupe, compress, allocate token budget, preserve provenance.

### `call_primary_llm`
**Input:** context pack and user message  
**Output:** answer or structured context request  
**Responsibilities:** make initial answer pass.

### `inspect_llm_output`
**Input:** model output  
**Output:** either final-answer path or second-pass path  
**Responsibilities:** parse JSON if `CONTEXT_REQUEST`, validate shape.

### `retrieve_second_pass_context`
**Input:** structured context request  
**Output:** targeted supplemental evidence  
**Responsibilities:** bounded second retrieval, smaller than first-pass pack.

### `compose_second_pass_pack`
**Input:** first-pass pack and supplemental evidence  
**Output:** second-pass pack  
**Responsibilities:** merge only incremental context.

### `call_second_pass_llm`
**Input:** second-pass pack  
**Output:** final answer  
**Responsibilities:** final answer generation.

### `attribute_answer`
**Input:** final answer and injected items  
**Output:** attribution records  
**Responsibilities:** estimate which items mattered.

### `score_usefulness`
**Input:** answer, attribution, feedback proxies  
**Output:** usefulness score  
**Responsibilities:** compute retrieval quality and context waste.

### `persist_episode`
**Input:** full broker state  
**Output:** persisted records  
**Responsibilities:** write episode, requests, items, attributions, scores.

## 23.3 Routing
```text
START
  -> normalize_request
  -> extract_query_features
  -> build_candidate_retrieval_plan
  -> score_and_select_plan
  -> retrieve_semantic_leaves
  -> retrieve_graph_anchors
  -> retrieve_policy_and_canonical
  -> rerank_candidates
  -> compose_context_pack
  -> call_primary_llm
  -> inspect_llm_output
      -> if final_answer: attribute_answer
      -> if context_request: retrieve_second_pass_context
                           -> compose_second_pass_pack
                           -> call_second_pass_llm
                           -> attribute_answer
  -> score_usefulness
  -> persist_episode
  -> END
```

## 23.4 Retry policy
- retrieval nodes: retry transient failures up to 2 times
- LLM call nodes: retry idempotent transport failures up to 2 times
- persistence nodes: retry until committed or dead-lettered
- second-pass nodes: never exceed configured loop cap

---

## 24. File and Module Layout Suggestion

```text
app/
  api/
    routes_query.py
    routes_feedback.py
    routes_replay.py
  broker/
    orchestrator.py
    state.py
    prompts.py
    composer.py
    attribution.py
  retrieval/
    planner.py
    scorer.py
    qdrant_client.py
    neo4j_client.py
    reranker.py
    policy_lookup.py
  schemas/
    api.py
    retrieval.py
    context.py
    feedback.py
  storage/
    postgres.py
    models.py
    migrations/
  ingestion/
    unstructured_pipeline.py
    embeddings.py
    graph_builder.py
  eval/
    phoenix.py
    usefulness.py
    replay.py
```

---

## 25. Recommended Next Implementation Artifacts

After this spec, the next best documents are:
- API OpenAPI contract
- PostgreSQL migration file set
- Neo4j constraint and index setup
- LangGraph implementation skeleton
- prompt contract for first-pass and second-pass LLM calls
- retrieval scorer formula and config file

---

## 26. One-line Operational Summary

This system should behave like a brokered memory-and-context engine that injects the smallest sufficient grounded context before the first model call, allows one structured escalation for more context, and gets better over time by learning which retrieval plans actually help.
