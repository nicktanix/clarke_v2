---
name: clarke-recall
description: "Query CLARKE memory and knowledge. Use when: 'what does clarke know about X', 'recall', 'search memory', 'ask clarke'"
---

# CLARKE Recall

## When to Use
- "what does clarke know about X"
- "recall our decision about Y"
- "search memory for Z"
- "ask clarke about..."
- "what's our policy on..."

## Workflow

### Step 1: Query CLARKE
Take the user's question and call `clarke_query`:

```json
{
  "message": "What is our convention for entity IDs?",
  "user_id": "current-user"
}
```

### Step 2: Present Results with Attribution

```
CLARKE Response
===============
[The answer]

Sources
-------
  - [source type]: [summary] (score: [confidence])

Metadata
--------
  Trace ID:      [trace_id]
  Degraded Mode: [yes/no]
```

Always show source attribution — it builds trust. If degraded mode is active, explain which retrieval paths were unavailable.

### Step 3: Feedback Loop
After showing the answer, ask: "Was this helpful?"

- **Yes** -> Call `clarke_feedback` with `accepted: true`
- **No** -> Ask what was wrong, suggest `/clarke-teach` to submit correction
- **Partially** -> Call `clarke_feedback` with `accepted: true` and note what was missing

### Step 4: Suggest Follow-ups
- "Want to dig deeper into a related topic?"
- "No results? Use `/clarke-teach` to add this knowledge"
- "This references a decision — want the full record?"

## Tools

| Tool | Purpose |
|------|---------|
| `clarke_query` | Send a query through the CLARKE broker |
| `clarke_feedback` | Submit feedback on response quality |

## Example

**User says:** "what does clarke know about our testing strategy"

**Agent does:**
1. Calls `clarke_query` with "what is our testing strategy"
2. Shows answer with sources and confidence scores
3. Asks "Was this helpful?"
4. On "yes" -> calls `clarke_feedback` with accepted=true
