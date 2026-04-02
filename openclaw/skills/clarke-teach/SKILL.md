---
name: clarke-teach
description: "Teach CLARKE through decisions, policies, corrections, and feedback. Use when: 'remember this', 'record decision', 'add policy', 'that was wrong'"
---

# CLARKE Learning Loop

## When to Use
- "remember this decision"
- "we decided to use X because Y"
- "always do X" / "never do Y"
- "clarke got this wrong"
- "that answer was wrong, actually it should be..."
- "that was great, remember that"

## Workflow

### Determine Teaching Type

Parse the user's input to identify one of four modes:

---

### Mode: Record a Decision

**Triggers:** "we decided", "the decision is", "record that we chose"

1. Ask for:
   - **Title**: Short name (e.g., "Use ULIDs for all entity IDs")
   - **Rationale**: Why this was decided
   - **Alternatives**: What else was considered and why it was rejected
   - **Decision maker**: Who decided (default: current user)

2. Call `clarke_create_decision` with the details

3. Confirm: "Decision recorded. CLARKE will reference this in future queries about this topic."

---

### Mode: Create a Policy

**Triggers:** "always", "never", "from now on", "the rule is", "add a policy"

1. Ask for:
   - **Policy content**: The rule in clear, actionable language
   - **Owner**: Who owns this (default: current user)

2. Call `clarke_create_policy`

3. Explain: "Policy created in draft status. It may need approval before influencing agent behavior. Use `/clarke-review` to check."

---

### Mode: Submit a Correction

**Triggers:** "that was wrong", "actually it should be", "incorrect"

1. Ask for:
   - **What was wrong**: The specific bad answer
   - **What it should be**: The correct answer
   - **Request ID** (if available): From the trace_id of the bad query

2. Call `clarke_feedback` with `accepted: false` and detailed notes

3. Explain: "Correction submitted. If enough similar corrections accumulate, CLARKE will propose a behavioral directive. Check `/clarke-review` periodically."

---

### Mode: Positive Feedback

**Triggers:** "that was great", "perfect", "exactly right"

1. Identify the request being praised
2. Call `clarke_feedback` with `accepted: true`
3. Confirm: "Positive feedback recorded. This helps CLARKE learn which patterns work."

## Tools

| Tool | Purpose |
|------|---------|
| `clarke_create_decision` | Record an architectural or process decision |
| `clarke_create_policy` | Create a new behavioral policy |
| `clarke_feedback` | Submit positive or negative feedback |

## Example

**User says:** "we decided to use structlog instead of stdlib logging because it gives us structured JSON output"

**Agent does:**
1. Recognizes as a Decision
2. Extracts title, rationale
3. Asks: "Were there alternatives considered?"
4. User: "considered stdlib logging and loguru"
5. Calls `clarke_create_decision`
6. Confirms: "Decision recorded: 'Use structlog for logging'"
