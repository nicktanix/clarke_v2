---
name: clarke-review
description: "Review CLARKE's self-improvement queue. Use when: 'review directives', 'pending proposals', 'what needs approval', 'approve directive'"
---

# CLARKE Review Queue

## When to Use
- "review pending directives"
- "what needs my attention in CLARKE"
- "approve that directive"
- "show the review queue"
- "any proposed changes"

## Workflow

### Step 1: Gather Pending Items

1. Call `clarke_list_agents` to get all active profile IDs
2. For each profile, call `clarke_list_directives` with `status: "pending_approval"`
3. Collect all pending proposals

### Step 2: Display Queue

```
CLARKE Review Queue
===================

Agent: Code Review Agent (code-review)
---------------------------------------
1. PROPOSED DIRECTIVE: "Always check for SQL injection in any database query construction"
   Cluster size: 5 corrections  |  Similarity: 0.87
   Source: 5 user corrections about SQL injection patterns

2. PROPOSED DIRECTIVE: "Prefer pytest fixtures over manual setup in test files"
   Cluster size: 3 corrections  |  Similarity: 0.82
   Source: 3 corrections about test conventions

Agent: CLARKE Operator (clarke-operator)
-----------------------------------------
   (no pending proposals)

Total: 2 items need review
```

### Step 3: Review Each Item

For each pending proposal, present options:
- **Approve**: Call `clarke_approve_directive`. This appends the directive to the agent's behavioral_directives and bumps the version.
- **Reject**: Ask for a reason, then call `clarke_reject_directive`.
- **Skip**: Move to the next item.

### Step 4: Summary

```
Review Complete
  Approved: 1
  Rejected: 1
  Skipped:  0

Agent "code-review" updated to version 4.
```

## Tools

| Tool | Purpose |
|------|---------|
| `clarke_list_agents` | Get all active agent profiles |
| `clarke_list_directives` | List pending directive proposals |
| `clarke_approve_directive` | Approve and apply a directive |
| `clarke_reject_directive` | Reject a directive with reason |

## Example

**User says:** "review the queue"

**Agent does:**
1. Lists 2 agents, finds 3 pending directives across them
2. Presents each with context (cluster size, similarity)
3. User approves 2, rejects 1 with reason "too specific"
4. Shows summary: 2 approved, 1 rejected, agents updated
