---
name: clarke-agent
description: "Manage CLARKE agent profiles and OpenClaw workspaces. Use when: 'create agent', 'list agents', 'new agent with workspace', 'update agent'"
---

# CLARKE Agent Management

## When to Use
- "create a new agent"
- "list agents" / "show agent profiles"
- "update the code-review agent"
- "set up an agent for deployment reviews"
- "create an agent with its own workspace"
- "archive an agent"

## Workflow

### Determine Intent
Parse the user's request to identify: **create**, **list**, **update**, or **archive**.

---

### Create Agent

Creating an agent involves two things:
1. A **CLARKE agent profile** (identity, capabilities, directives — stored in CLARKE)
2. Optionally, an **OpenClaw workspace** (SOUL.md, AGENTS.md, etc. — on disk)

#### Step 1: Gather Agent Details
Ask for (or extract from context):
- **Name**: Human-readable (e.g., "Code Review Agent")
- **Slug**: Auto-suggest from name (e.g., "code-review")
- **Model**: Default `claude-sonnet-4-20250514`
- **Capabilities**: Suggest from common list below
- **Behavioral directives**: Rules the agent must follow
- **Budget tokens**: Default 8000
- **Create workspace?**: Ask if they want a full OpenClaw workspace

#### Step 2: Create CLARKE Profile
Call `clarke_create_agent` with the profile data.

#### Step 3: Scaffold OpenClaw Workspace (if requested)
If the user wants a workspace, create the directory structure:

```bash
# Create workspace directory
mkdir -p ~/.openclaw/workspace-<slug>

# Write SOUL.md with the agent's persona
cat > ~/.openclaw/workspace-<slug>/SOUL.md << 'EOF'
# <Agent Name>

## Directives
- <directive 1>
- <directive 2>

## Capabilities
<capabilities list>
EOF

# Write AGENTS.md with CLARKE connection
cat > ~/.openclaw/workspace-<slug>/AGENTS.md << 'EOF'
# CLARKE-Managed Agent
Context is dynamically managed by CLARKE.
Use /clarke for status.
EOF

# Run CLARKE installer to wire up the workspace
cd ~/.clarke
python openclaw/install.py \
    --workspace ~/.openclaw/workspace-<slug> \
    --agent-slug <slug> \
    --reconfigure --skip-backend --skip-superpowers
```

This wires the new workspace to CLARKE with its own isolated project, MCP server, and context injection hooks.

#### Step 4: Configure OpenClaw Routing (if multi-agent)
If the user has multiple agents, explain how to route channels to workspaces in `openclaw.json`:

```json5
{
  agents: {
    list: [
      { id: "<slug>", workspace: "~/.openclaw/workspace-<slug>" }
    ]
  }
}
```

**Common capabilities to suggest:**
`code_review`, `testing`, `docs`, `deployment`, `security`, `debugging`, `architecture`, `data_analysis`, `devops`, `frontend`, `backend`, `api_design`, `performance`, `clarke-admin`, `skill-management`

---

### List Agents

1. Call `clarke_list_agents` with tenant_id
2. Display as a table:

```
Agent Profiles
| Name              | Slug          | Capabilities        | Version |
|-------------------|---------------|---------------------|---------|
| CLARKE Operator   | clarke-op     | clarke-admin, ...   | 3       |
| Code Review Agent | code-review   | code_review, ...    | 1       |
```

---

### Update Agent

1. Call `clarke_list_agents` to show options
2. Ask which agent and what to change
3. Call `clarke_update_agent` with the changes
4. Show the updated profile (version should be bumped)
5. If the agent has a workspace, note that context will update automatically on next session (via the before_prompt_build hook)

---

### Archive Agent

1. Confirm the agent to archive
2. Explain: archiving soft-deletes the CLARKE profile. The workspace files remain on disk.
3. Proceed only after explicit confirmation

## Tools

| Tool | Purpose |
|------|---------|
| `clarke_create_agent` | Create a CLARKE agent profile |
| `clarke_list_agents` | List active agent profiles |
| `clarke_update_agent` | Update an existing profile |

## Example: Create Agent with Workspace

**User says:** "create a security review agent with its own workspace"

**Agent does:**
1. Suggests: name="Security Review Agent", slug="security-review"
2. Suggests capabilities: security, code_review, vulnerability_assessment
3. Suggests directives: "Flag OWASP Top 10 vulnerabilities", "Check for hardcoded secrets"
4. Calls `clarke_create_agent` → profile created
5. Creates `~/.openclaw/workspace-security-review/` with SOUL.md and AGENTS.md
6. Runs the CLARKE installer to wire up MCP, hooks, and skills
7. Shows: "Agent created. Start it with: `openclaw agent start --workspace ~/.openclaw/workspace-security-review`"
