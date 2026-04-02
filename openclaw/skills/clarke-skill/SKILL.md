---
name: clarke-skill
description: "Author and ingest skills into CLARKE. Use when: 'create skill', 'new skill', 'teach clarke a skill', 'add capability'"
---

# CLARKE Skill Authoring

## When to Use
- "create a new skill"
- "teach clarke a skill for code reviews"
- "add a deployment checklist skill"
- "I want to make a skill that..."
- "import this as a skill"

## Workflow

### Author a New Skill

Walk the user through skill creation interactively:

1. **What should the skill do?** Get a natural language description.

2. **Name it**: Suggest a kebab-case name (e.g., "deployment-checklist")

3. **Write the content**: Draft the skill as markdown. Include:
   - Clear trigger conditions (when to use this skill)
   - Step-by-step workflow
   - Tool references (if the skill uses MCP tools)
   - At least one concrete example
   - A checklist if the workflow has discrete steps

4. **Set metadata**:
   - `trigger_conditions`: List of phrases that should activate this skill
   - `agent_capabilities`: Which agent types should have access (e.g., ["deployment", "devops"])
   - `priority`: 1 (always include if matched) through 5 (only if highly relevant)

5. **Ingest into CLARKE**: Call `clarke_ingest_skill` with the full content and metadata

6. **Optionally create Claude Code skill**: Also write the skill as `.claude/skills/clarke/{name}/SKILL.md` so it's available as a slash command

### Import from File

If the user points to an existing file:
1. Read the file
2. Extract or generate metadata
3. Call `clarke_ingest_skill`

## Skill Content Template

```markdown
# [Skill Title]

## When to Use
- [trigger phrase 1]
- [trigger phrase 2]

## Workflow
1. [Step 1]
2. [Step 2]
3. [Step 3]

## Tools
| Tool | Purpose |
|------|---------|
| `tool_name` | what it does |

## Checklist
- [ ] Step 1 done
- [ ] Step 2 done

## Example
[Concrete walkthrough]
```

## Tools

| Tool | Purpose |
|------|---------|
| `clarke_ingest_skill` | Store skill in CLARKE's Qdrant |

## Example

**User says:** "create a skill for PR review checklists"

**Agent does:**
1. Suggests name: "pr-review-checklist"
2. Drafts content with sections: code quality, testing, security, documentation
3. Sets trigger_conditions: ["review PR", "pull request checklist", "code review"]
4. Sets agent_capabilities: ["code_review"]
5. Calls `clarke_ingest_skill`
6. Offers to also write as `.claude/skills/clarke/pr-review-checklist/SKILL.md`
