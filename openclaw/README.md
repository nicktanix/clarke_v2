# openclaw-clarke

CLARKE (Cognitive Learning Augmentation Retrieval Knowledge Engine) plugin for [OpenClaw](https://github.com/openclaw/openclaw).

Gives your OpenClaw agent persistent memory, learned context, and self-improving skills — all injected programmatically into every LLM call.

## Install

```bash
openclaw plugins install openclaw-clarke
```

## What It Does

- **Every LLM call** gets CLARKE context injected into the system prompt (policies, decisions, skills, domain knowledge)
- **Every user query** gets retrieval-augmented with relevant documents, memory, and decisions
- **Every response** feeds back into CLARKE's learning loop for continuous improvement

## Hooks

| Hook | Purpose |
|------|---------|
| `agent:bootstrap` | Inject CLARKE identity into bootstrap files |
| `before_prompt_build` | Inject session context (cached 60s) into system prompt |
| `before_agent_reply` | Query-specific RAG augmentation |
| `session_start` | Greeting + cache invalidation + auto-registration |
| `llm_output` | Implicit feedback for learning loop |

## Tools

| Tool | Description |
|------|-------------|
| `clarke_status` | System health, agents, policies |
| `clarke_recall` | Query CLARKE memory |
| `clarke_teach` | Submit knowledge and corrections |
| `clarke_review` | List pending directive proposals |

## Commands

| Command | Description |
|---------|-------------|
| `/clarke` | Dashboard |
| `/clarke_recall <question>` | Query memory |
| `/clarke_teach <knowledge>` | Teach CLARKE |

## Prerequisites

CLARKE backend must be running. See the [setup guide](https://github.com/nicktanix/clarke_v2#openclaw).

## Configuration

Set these environment variables (or configure via `openclaw.json`):

```bash
CLARKE_API_URL=http://localhost:8000
CLARKE_TENANT_ID=<auto-registered>
CLARKE_PROJECT_ID=<auto-registered>
CLARKE_AGENT_SLUG=clarke-operator
```

Tenant and project IDs are auto-registered from the workspace path on first session start.

## License

Polyform Noncommercial 1.0.0 — free for personal and noncommercial use.
For commercial licensing: nick@neill.cloud
