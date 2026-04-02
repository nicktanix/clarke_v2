---
name: clarke-configure
description: "View and modify CLARKE configuration. Use when: 'configure clarke', 'show settings', 'enable self-improvement', 'clarke config'"
---

# CLARKE Configuration

## When to Use
- "show CLARKE settings"
- "configure clarke"
- "enable self-improvement"
- "what features are available"
- "change the token budget"

## Workflow

### Step 1: Current Status
Call `clarke_health` for system version and health. Read `clarke/settings.py` to show all available settings.

### Step 2: Display Settings

Group by category:

```
CLARKE Configuration
====================

Feature Flags
  CLARKE_SESSION_CONTEXT_ENABLED = false  <- Dynamic agent context from CLARKE
  CLARKE_SELF_IMPROVEMENT_ENABLED = false <- Directive surfacing + skill effectiveness
  CLARKE_GRAPH_ENABLED = true             <- Neo4j graph retrieval
  CLARKE_OTEL_ENABLED = false             <- OpenTelemetry tracing

LLM
  CLARKE_DEFAULT_ANSWER_MODEL = gpt-4o-mini
  CLARKE_ANSWER_TEMPERATURE = 0.0
  CLARKE_REQUEST_TIMEOUT_MS = 30000

Retrieval
  CLARKE_SEARCH_TOP_K = 20
  CLARKE_RERANK_TOP_K = 5
  CLARKE_RERANK_ENABLED = true

Agent Context
  CLARKE_DEFAULT_SESSION_BUDGET_TOKENS = 8000
  CLARKE_MAX_SKILLS_PER_SESSION = 10

Self-Improvement
  CLARKE_SKILL_EFFECTIVENESS_LEARNING_RATE = 0.05
  CLARKE_DIRECTIVE_MIN_CLUSTER_SIZE = 3
  CLARKE_DIRECTIVE_SIMILARITY_THRESHOLD = 0.80
```

### Step 3: Modify Settings

Settings come from environment variables. To change them:
1. Edit the `.env` file (or create one) in the project root
2. Set the variable: `CLARKE_SESSION_CONTEXT_ENABLED=true`
3. Restart CLARKE: `make dev`

Use the Edit tool to update the `.env` file when the user requests changes.

### Feature Toggle Guide

| Feature | Variable | What It Does |
|---------|----------|-------------|
| Session Context | `SESSION_CONTEXT_ENABLED` | Agents get dynamic context from CLARKE at session start |
| Self-Improvement | `SELF_IMPROVEMENT_ENABLED` | Skill effectiveness learning + directive surfacing |
| Graph Memory | `GRAPH_ENABLED` | Neo4j traversal for relationship-based retrieval |
| Telemetry | `OTEL_ENABLED` | OpenTelemetry distributed tracing |
| Reranking | `RERANK_ENABLED` | Cross-encoder reranking of retrieved items |

## Tools

| Tool | Purpose |
|------|---------|
| `clarke_health` | System health and version |

## Example

**User says:** "enable self-improvement"

**Agent does:**
1. Reads current `.env` (or notes it doesn't exist)
2. Adds/updates: `CLARKE_SELF_IMPROVEMENT_ENABLED=true`
3. Explains: "Self-improvement enabled. CLARKE will now track skill effectiveness from feedback and surface directive proposals when recurring corrections are detected. Use `/clarke-review` to manage proposals. Restart CLARKE for changes to take effect."
