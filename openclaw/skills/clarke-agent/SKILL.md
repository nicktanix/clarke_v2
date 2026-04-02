---
name: clarke-agent
description: "Manage CLARKE agent profiles. Use when: 'create agent', 'list agents', 'update agent', 'new agent profile'"
---

# CLARKE Agent Management

## When to Use
- "create a new agent"
- "list agents" / "show agent profiles"
- "update the code-review agent"
- "archive an agent"
- "set up an agent for deployment reviews"

## Workflow

### Determine Intent
Parse the user's request to identify: **create**, **list**, **update**, or **archive**.

---

### Create Agent

1. Ask for (or extract from context):
   - **Name**: Human-readable (e.g., "Code Review Agent")
   - **Slug**: Auto-suggest from name (e.g., "code-review")
   - **Model**: Default `claude-sonnet-4-20250514`
   - **Capabilities**: Suggest from common list below
   - **Tool access**: Which MCP tools this agent can use
   - **Behavioral directives**: Rules the agent must follow
   - **Budget tokens**: Default 8000

2. Call `clarke_create_agent` with the profile data

3. Confirm with the created profile details

**Common capabilities to suggest:**
`code_review`, `testing`, `docs`, `deployment`, `security`, `debugging`, `architecture`, `data_analysis`, `devops`, `frontend`, `backend`, `api_design`, `performance`, `clarke-admin`, `skill-management`

---

### List Agents

1. Call `clarke_list_agents` with tenant_id
2. Display as a table:

```
Agent Profiles
| Name              | Slug          | Model              | Capabilities       | Version |
|-------------------|---------------|--------------------|--------------------|---------|
| CLARKE Operator   | clarke-op     | claude-sonnet-4-.. | clarke-admin, ...  | 3       |
| Code Review Agent | code-review   | claude-sonnet-4-.. | code_review, ...   | 1       |
```

---

### Update Agent

1. Call `clarke_list_agents` to show options
2. Ask which agent and what to change
3. Call `clarke_update_agent` with the changes
4. Show the updated profile (version should be bumped)

---

### Archive Agent

1. Confirm the agent to archive
2. Explain: archiving soft-deletes the profile — it stops being used for session context but remains in the database for audit
3. Proceed only after explicit confirmation

## Tools

| Tool | Purpose |
|------|---------|
| `clarke_create_agent` | Create a new agent profile |
| `clarke_list_agents` | List active agent profiles |
| `clarke_update_agent` | Update an existing profile |

## Example

**User says:** "create an agent for security reviews"

**Agent does:**
1. Suggests: name="Security Review Agent", slug="security-review"
2. Suggests capabilities: security, code_review, vulnerability_assessment
3. Suggests directives: "Flag OWASP Top 10 vulnerabilities", "Check for hardcoded secrets", "Verify input validation at system boundaries"
4. Calls `clarke_create_agent`
5. Shows created profile with ID
