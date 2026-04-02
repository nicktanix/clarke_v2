/**
 * agent:bootstrap hook — inject CLARKE identity into OpenClaw bootstrap files.
 *
 * Fires before workspace bootstrap files are injected into the system prompt.
 * We add a lightweight AGENTS.md with CLARKE connection metadata so the agent
 * knows CLARKE is active from the start.
 */

import { getClarkeConfig } from "../clarke-client.js";

export async function handleBootstrap(event: any): Promise<void> {
  const config = getClarkeConfig();
  if (!config) return;

  const bootstrapContent = `# CLARKE-Managed Agent

This agent's context is dynamically managed by CLARKE (Cognitive Learning
Augmentation Retrieval Knowledge Engine). Policies, decisions, skills,
and domain knowledge are injected into every prompt automatically via
the before_prompt_build hook.

## Available Commands
- /clarke — system dashboard and status
- /clarke-agent — manage agent profiles
- /clarke-skill — author and ingest skills
- /clarke-teach — record decisions, policies, corrections
- /clarke-recall — query CLARKE memory
- /clarke-review — approve self-improvement proposals
- /clarke-ingest — feed documents into CLARKE
- /clarke-configure — view and modify settings

## How Context Works
CLARKE injects context before every LLM call. You don't need to read
files or query memory manually — relevant policies, decisions, skills,
and domain knowledge are already in your system prompt. When sources
conflict, follow the trust ordering: Policy > Decisions > Documents >
Episodic Memory > Semantic Neighbors.

## Learning Loop
Every interaction builds CLARKE's memory. When users correct you, those
corrections accumulate and may become behavioral directives. Encourage
users to provide feedback — it directly improves future responses.
`;

  event.context?.bootstrapFiles?.push({
    basename: "AGENTS.md",
    content: bootstrapContent,
  });
}
