# Brokered Context Memory System
## Canonical Unified Specification (v3)

---

## 1. Purpose

A broker-governed context system that:
- injects minimal sufficient context before model execution
- supports controlled escalation (context or sub-agents)
- enforces strict tenancy, security, and auditability
- continuously improves retrieval quality

---

## 2. Core Principles

- Broker owns all memory, retrieval, and execution boundaries
- Prefer retrieval over delegation
- Sub-agents are bounded, ephemeral, and isolated
- Context must be minimal, grounded, and attributable
- System must degrade safely

---

## 3. System Architecture

### Components
- Broker (control plane)
- Retrieval layer (Qdrant + hybrid search)
- Graph memory (Neo4j)
- Canonical store (PostgreSQL)
- Execution engine (LangGraph)
- Model gateway (LiteLLM)

---

## 4. Execution Flow

1. Receive request
2. Plan retrieval
3. Build context pack (anchors → evidence)
4. Model call
5. Inspect response:
   - Answer
   - CONTEXT_REQUEST
   - SUBAGENT_SPAWN
6. Optional second pass
7. Persist episode

---

## 5. Sub-Agent System

### Rules
- Max depth: 5
- No shared mutable memory
- Broker-mediated memory only
- No sibling communication (V1)

### Handoff Modes
- copy_in
- reference_link
- hybrid

### Spawn Criteria
- task must be separable
- output must be structured
- retrieval must be insufficient

---

## 6. Data Model

### Core Tables
- episodes
- retrieval_items
- policies
- decisions

### Agent Tables
- agent_instances
- agent_memory_links
- subagent_results

---

## 7. Retrieval System

- Hybrid (semantic + lexical)
- Reranking (cross-encoder)
- Deduplication
- Token-accurate budgeting
- Blended scoring (semantic + graph + recency + trust)

---

## 8. Memory Layers

- Semantic (vector)
- Graph (relationships)
- Decision (rationale)
- Policy (canonical truth)

Precedence:
policy > decisions > evidence > episodic

---

## 9. Learning Loop

- Retrieval plan optimization
- Epsilon-greedy exploration
- Proto-class clustering (HDBSCAN)
- Replay-based evaluation

---

## 10. Observability

Metrics:
- Useful Context Ratio
- Context waste
- Groundedness
- Latency (p50/p95)
- Hallucination rate

All actions are audit logged.

---

## 11. Security & Governance

- Tenant isolation everywhere
- PII redaction before indexing
- RBAC for policy changes
- Append-only audit logs
- Circuit breakers + degraded modes

---

## 12. Degraded Modes

- Full: all features
- Reduced: limited sub-agents
- Canonical-only: policy + decision memory only

---

## 13. Execution Graph Nodes

- retrieve
- rerank
- compose_context
- call_model
- inspect_context_request
- inspect_subagent_spawn
- validate_spawn
- create_subagent
- consume_result

---

## 14. Operational Summary

A broker-first, tenant-safe, learning context system that:
- injects minimal grounded context
- allows one structured escalation
- supports bounded sub-agent execution
- continuously improves via feedback

---

## End of Spec
