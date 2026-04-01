# Brokered Context Memory System
## Canonical Unified Specification (v3.1)

---

## 1. Purpose

A broker-governed context and memory system that:
- injects the smallest sufficient grounded context before any model call
- supports controlled escalation via additional context requests or sub-agent spawning
- enforces strict multi-tenancy, security, privacy, and auditability
- continuously improves retrieval and planning quality through online learning
- enables hierarchical agent execution where parent agents can dynamically spawn isolated runtime sub-agents, each receiving a fully brokered, task-specific context pack

---

## 2. Core Principles

- The broker owns all retrieval, memory access, and context composition — no LLM has direct memory access
- Prefer targeted retrieval over delegation; spawn sub-agents only when a task is clearly separable and retrieval is insufficient
- Sub-agents are bounded, ephemeral, and strictly isolated runtime instances
- Context must be minimal, grounded, attributable, and token-budget-aware
- All operations enforce tenant isolation, PII redaction, and append-only audit logging
- The system must degrade safely when dependencies fail
- Classes and retrieval strategies are earned through usage patterns, not predefined taxonomies

---

## 3. System Architecture

### Core Components
- **Broker API** (FastAPI) — entry point with auth, rate limiting, and tenant enforcement
- **Execution Engine** (LangGraph) — orchestrates flows with checkpoints and degraded-mode routing
- **Retrieval Layer** — hybrid semantic + lexical (Qdrant), graph-aware (Neo4j GraphRAG)
- **Canonical Store** (PostgreSQL) — structured truth, policy, decisions, episodes, lineage, and audit logs
- **Model Gateway** (LiteLLM) — standardized calls with exact tokenizer-based token counting
- **Background Engine** (Temporal) — ingestion, clustering, reweighting, and replay

### Cross-Cutting Requirements
- Tenant isolation (`tenant_id`, `project_id`, `user_id`) enforced at every retrieval and persistence layer
- Mandatory PII/sensitive-data redaction before indexing in vector or graph stores
- Exact token counting using the target answer model’s tokenizer
- Circuit breakers and per-node timeouts around all external services
- `degraded_mode` flag propagated through the entire flow
- Prompt and planner weight versioning

---

## 4. Execution Flow

1. Receive request (user or parent-agent) with tenant scoping
2. Extract query features and generate retrieval plan candidates (with ε-greedy exploration)
3. Execute retrieval (hybrid semantic + graph) with timeouts and tenant filters
4. Rerank candidates and compose smallest-sufficient context pack (anchors first, deduplicated evidence)
5. Call primary LLM with constitutional prompt + context pack
6. Inspect structured output:
   - Final answer
   - `CONTEXT_REQUEST` (bounded second pass)
   - `SUBAGENT_SPAWN` (create runtime sub-agent)
7. Optional second-pass or sub-agent creation
8. Attribute, score usefulness, persist episode with full lineage, and update learned weights

---

## 5. Sub-Agent System

### Rules
- Maximum depth: 5 (configurable, enforced by broker)
- Sub-agents are ephemeral runtime instances with their own isolated context and episode history
- No shared mutable memory between agents; all handoff is broker-mediated
- No direct sibling communication in V1 (parent remains coordinator)
- All sub-agent actions inherit tenant isolation, redaction, and audit rules

### Handoff Modes
- **copy_in**: Selected evidence and policy fragments are copied into the sub-agent’s initial context pack
- **reference_link**: Sub-agent receives lightweight references/links; broker resolves on demand during its retrieval
- **hybrid** (default): Combination of copied high-priority items + references for broader context

### Spawn Criteria (enforced by broker)
- Task must be clearly separable and well-scoped
- Output should be structured when possible
- Retrieval alone must be judged insufficient by the parent LLM
- Spawn request must pass depth quota and tenant validation

### Spawn Process
When LLM returns a `SUBAGENT_SPAWN` structure:
1. Broker validates request and creates `agent_instance` record
2. Builds inherited context pack using selected handoff mode
3. Records lineage (`PARENT_OF` edge in Neo4j and `agent_memory_links` in PostgreSQL)
4. Returns sub-agent handle and initial context pack to parent
5. Parent delegates via subsequent `/query` calls using the sub-agent handle

Sub-agents use the identical broker flow and contribute to the shared learning loop.

---

## 6. Data Model

### Core Tables (PostgreSQL)
- `retrieval_episodes`
- `retrieval_requests`
- `retrieved_items`
- `answer_attributions`
- `usefulness_scores`
- `policy_nodes` (with approval workflow)
- `prompt_versions`
- `audit_events` (append-only)

### Agent-Specific Tables
- `agent_instances` (id, tenant_id, parent_agent_id, task_definition, depth, status)
- `agent_memory_links` (parent_episode_id, child_episode_id, handoff_mode, inherited_item_ids)
- `subagent_results`

### Graph Extensions (Neo4j)
- New node label: `AgentInstance`
- New edge type: `PARENT_OF` (with `handoff_reason`, `handoff_mode`)

---

## 7. Retrieval System

- Hybrid search (vector + BM25) in Qdrant with mandatory tenant filters
- Cross-encoder reranking (plus optional lightweight LLM reranker for design queries)
- Semantic deduplication and merged provenances
- Blended scoring: semantic + lexical + graph + recency + trust + cost_penalty
- Leaf-first retrieval followed by convergence anchors
- Exact token budgeting with dynamic multipliers based on query features

---

## 8. Memory Layers & Precedence

Memory types (distinct but connected):
- Policy (canonical truth)
- Decision (tradeoffs and rationale)
- Document / Semantic (chunks and facts)
- Episodic (summarized history)
- Graph (relationships and lineage)

**Explicit precedence (stated in prompt):**
1. Canonical policy
2. Structured decision records
3. Authoritative document chunks
4. Recent episodic summaries
5. Generic semantic neighbors

Conflicts must be surfaced explicitly with source attribution.

---

## 9. Learning Loop

- Online weight updates for source priors, rewrite templates, graph strategies, and blending coefficients
- ε-greedy exploration (initial 0.05–0.10, decaying over time)
- Retrieval episode embedding and periodic HDBSCAN clustering to form proto-classes
- Proto-class promotion based on member count, stability, and usefulness improvement
- Replay harness in Phoenix for comparing planner variants
- Usefulness signals include Useful Context Ratio, groundedness, and low waste

---

## 10. Observability & Evals

**Key Metrics:**
- Useful Context Ratio (attributed tokens / total injected tokens)
- Context waste ratio
- Groundedness and hallucinated-constraint rate
- Retrieval precision and usefulness by source/strategy
- Loop invocation rate and second-pass success rate
- Degraded mode activation rate
- Proto-class stability over time

All actions are fully traceable via OpenTelemetry with `request_id` and `degraded_mode` propagated.

---

## 11. Security & Governance

- Tenant isolation enforced via payload filters (Qdrant), query predicates (Neo4j), and row-level security (PostgreSQL)
- Mandatory PII/sensitive-data scrubbing during ingestion and episodic summarization
- RBAC and approval workflow required before policy becomes canonical
- Append-only audit logs for every memory write, spawn, and policy change
- Per-user and per-tenant token budgets and second-pass quotas

---

## 12. Degraded Modes

- **Full**: hybrid retrieval + graph + sub-agent spawning
- **Reduced**: semantic retrieval + policy/decisions (limited sub-agents)
- **Canonical-only**: policy + structured decisions only (no sub-agents)

Degraded mode is explicitly logged and influences learning signals.

---

## 13. Execution Graph Nodes (LangGraph)

Key nodes include:
- `validate_request_and_tenant`
- `extract_query_features`
- `build_candidate_retrieval_plan`
- `check_dependency_health`
- `retrieve_semantic_and_graph`
- `rerank_and_compose_context`
- `call_answer_model`
- `inspect_structured_output`
- `handle_context_request`
- `inspect_subagent_spawn`
- `validate_and_create_subagent`
- `build_inherited_context_pack`
- `persist_episode_and_lineage`
- `score_usefulness`

State includes `degraded_mode`, `prompt_version_id`, `agent_instance_id`, and full tenant scoping.

---

## 14. Operational Summary

A tenant-safe, broker-first, learning context engine that injects the smallest sufficient grounded context before every model call (user or sub-agent), supports one structured escalation for more context or bounded sub-agent creation with mediated handoff, degrades safely, maintains full auditability and lineage, and continuously improves retrieval plans and emergent classifications through real usage feedback.

---

## End of Spec
