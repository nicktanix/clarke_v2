---
name: clarke
description: "CLARKE dashboard and system status. Use when: 'clarke status', 'show dashboard', 'system state', 'what commands are available'"
---

# CLARKE Dashboard & Status

## When to Use
- "clarke status"
- "show me the dashboard"
- "what's the system state"
- "is clarke healthy"
- "what can clarke do"

## Workflow

### Step 1: Gather System State
Run these MCP tool calls in parallel:

1. `clarke_health` -- get system health, version, component status
2. `clarke_list_agents` -- get all registered agent profiles
3. `clarke_list_policies` -- get all active policies

### Step 2: Format Dashboard Output

Present the results as a structured dashboard:

```
CLARKE Command Center
=====================

System Health
  Status:    [healthy/degraded/down]
  Version:   [version from health]
  Components:
    - PostgreSQL: [status]
    - Qdrant:     [status]
    - LiteLLM:    [status]
    - Neo4j:      [status or "disabled"]

Active Agents ([count])
  [table: name | slug | model | capabilities]

Active Policies ([count])
  [table: title | owner | created]

Available Commands
  /clarke            This dashboard
  /clarke-agent      Create, list, update agent profiles
  /clarke-skill      Author and ingest new skills
  /clarke-teach      Record decisions, policies, corrections
  /clarke-recall     Query CLARKE memory
  /clarke-review     Review pending directive proposals
  /clarke-ingest     Ingest files and documents
  /clarke-configure  View and modify settings
```

### Step 3: Surface Actionable Items
If there are degraded components, suggest `/clarke-configure` to check settings.
If there are no agents, suggest `/clarke-agent` to create one.
If there are pending directives (check via `clarke_list_directives`), mention the count and suggest `/clarke-review`.

## Tools

| Tool | Purpose |
|------|---------|
| `clarke_health` | System health and component status |
| `clarke_list_agents` | All registered agent profiles |
| `clarke_list_policies` | Active policies |
| `clarke_list_directives` | Check for pending approvals |

## Example

**User says:** "clarke status"

**Agent does:**
1. Calls `clarke_health` -> healthy, all components green
2. Calls `clarke_list_agents` -> 2 agents
3. Calls `clarke_list_policies` -> 1 policy

**Agent outputs the dashboard with health, agents, policies, and available commands.**
