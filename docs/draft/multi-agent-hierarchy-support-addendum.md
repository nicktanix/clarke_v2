# Brokered Context Memory System
## Multi-Agent Hierarchy Support Addendum

This addendum extends the brokered context system with **bounded hierarchical sub-agent support** while preserving the core architectural rule that the **broker owns retrieval, memory access, execution boundaries, and policy enforcement**.

---

## 5. Core Architectural Principles (Additions)

### 5.9 Hierarchical agent spawning with brokered handoff
Parent agents may request creation of runtime sub-agents via a structured `SUBAGENT_SPAWN` response. The broker alone creates the sub-agent instance, assembles its initial context pack from approved parent context plus explicit handoff inputs, and returns a scoped handle.

### 5.10 Sub-agents are task-scoped, broker-governed execution units
Sub-agents are ephemeral runtime instances created only for separable sub-tasks. They are not unrestricted autonomous workers, do not receive direct storage access, and do not share mutable working memory with parent agents.

### 5.11 Prefer retrieval before delegation
The system must prefer `CONTEXT_REQUEST` over `SUBAGENT_SPAWN` unless the requested work is clearly separable, well-scoped, and benefits from isolated execution.

---

## 6. Cross-Cutting Non-Functional Requirements (Additions)

### 6.5 Hierarchical execution constraints
- Sub-agent depth must be bounded. Default maximum depth: `5`.
- Total active sub-agents must be quota-limited per tenant, project, and root request.
- Sub-agent creation must be budget-limited by token, time, and concurrency thresholds.
- Sub-agent spawning is disabled in canonical-only degraded mode.
- In reduced degraded mode, sub-agent spawning is allowed only for narrow read-only tasks.

### 6.6 Memory inheritance and isolation
- Sub-agents do not share mutable working memory with parent agents.
- Sub-agents receive a broker-assembled inherited context pack plus optional broker-mediated access to approved linked memory.
- Parent-to-child handoff must follow one of these modes:
  - `copy_in`: a point-in-time context snapshot is passed to the child
  - `reference_link`: the child may retrieve only from broker-approved linked artifacts
  - `hybrid`: combines `copy_in` and `reference_link`
- Child agents may not write directly into parent memory.
- Child results may be promoted into parent-visible memory only through broker-controlled result ingestion.

### 6.7 Hierarchy communication rules
- V1 supports only:
  - parent -> child delegation
  - child -> broker result return
  - parent -> child follow-up via broker handle
- Child-to-child communication is not allowed in V1.
- Sibling coordination primitives are out of scope for V1.

### 6.8 Spawn approval policy
A `SUBAGENT_SPAWN` request may only be approved when all of the following are true:
- the requested task is clearly scoped and separable
- the task has a defined output shape
- the task cannot be more efficiently satisfied by a `CONTEXT_REQUEST`
- tenant, project, and policy constraints allow the spawn
- depth, budget, and concurrency limits allow the spawn
- the required memory sources are allowed for the child scope

---

## 7. Major Components (Additions)

## 7.2 Execution Graph (Updated)
The execution graph must support a structured sub-agent spawn path after the model response inspection stage.

### New routing behavior
After `inspect_for_context_request`, the graph must also evaluate `inspect_for_subagent_spawn`.

If the model returns `SUBAGENT_SPAWN`, the broker must:
1. validate the spawn request
2. enforce depth, budget, and quota limits
3. create a runtime sub-agent instance
4. build the inherited context pack
5. persist lineage
6. return a scoped sub-agent handle and initial context

### Degraded-mode rules
- **Full mode**: sub-agent spawning allowed
- **Reduced mode**: sub-agent spawning allowed only for narrow read-only tasks
- **Canonical-only mode**: sub-agent spawning disabled

---

## 7.3 Canonical System-of-Record (Additions)

### New tables

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

### Requirements
- all sub-agent records must be tenant-scoped
- all lifecycle transitions must be auditable
- child instances must be expirable and garbage-collectable
- replay must preserve lineage without duplicating runtime side effects

---

## 7.5 Graph Memory (Additions)

### New node / edge semantics

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

### Requirements
- lineage edges must preserve tenant and project scoping
- child lineage must be queryable for replay, eval, and debugging
- graph traversal for lineage must remain separate from user-facing memory retrieval unless explicitly needed

---

## 8. Online Request Flow (Additions)

## 8.11 Step 11: Sub-agent spawn
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

Sub-agents then use the same `/query` broker flow as any top-level request, but within their scoped runtime boundary.

---

## 9. Prompt Architecture (Additions)

Add the following to the constitutional prompt:

> You may request creation of a specialized sub-agent only for a well-scoped separable sub-task. Use the `SUBAGENT_SPAWN` JSON format. Prefer `CONTEXT_REQUEST` when additional context is sufficient. The broker will decide whether a sub-agent is appropriate, what memory it may receive, and what context is inherited. You remain responsible for the overall task.

### Additional prompt rules
- spawning is for decomposition, not unrestricted delegation
- the child receives only broker-approved memory
- the parent remains accountable for integrating child outputs
- sub-agent requests must be minimal and well-scoped

---

## 14. Data Contracts (Additions)

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

## 20. PostgreSQL Schema Plan (Additions)

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

## 22. LangGraph Node Plan (Additions)

### New nodes
- `inspect_for_subagent_spawn`
- `validate_subagent_spawn`
- `create_subagent_instance`
- `build_inherited_context_pack`
- `persist_agent_lineage`
- `consume_subagent_result`
- `garbage_collect_subagent`

### Additional state fields
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

## 24. MVP and V1 Scope (Additions)

### Strongly recommended for V1
- sub-agent spawn support via structured output
- runtime instance creation and expiry
- agent lineage tracking in PostgreSQL and Neo4j
- structured child result ingestion

### Can wait until V2
- advanced sub-agent coordination primitives
- sibling coordination
- shared result aggregation tools
- persistent role-specialized agent families

---

## 26. One-Line Operational Summary (Updated)

This system should behave like a tenant-safe, hierarchical brokered memory-and-context engine that injects the smallest sufficient grounded context before any model call, allows one structured escalation for more context or the creation of a new runtime sub-agent with inherited memory, degrades safely when dependencies fail, and gets better over time by learning which retrieval plans actually help across entire agent hierarchies.
