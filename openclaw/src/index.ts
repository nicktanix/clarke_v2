/**
 * CLARKE plugin for OpenClaw — native context injection + query augmentation.
 *
 * Hooks into OpenClaw's plugin system to:
 * 1. Inject CLARKE session context into every system prompt (before_prompt_build)
 * 2. Augment user queries with retrieval-specific context (before_agent_reply)
 * 3. Feed interactions back for learning (llm_output)
 *
 * No file writing, no markdown parsing — context goes directly into the
 * prompt pipeline programmatically.
 *
 * Hook events handled:
 * - agent:bootstrap       — inject CLARKE identity into bootstrap files
 * - before_prompt_build   — inject session context (cached, 60s TTL)
 * - before_agent_reply    — query-specific RAG augmentation
 * - session_start         — invalidate cache, output greeting
 * - llm_output            — implicit feedback for learning loop
 */

import { TTLCache } from "./cache.js";
import { handleBeforeReply } from "./hooks/before-reply.js";
import { handleBootstrap } from "./hooks/bootstrap.js";
import { handleLlmOutput } from "./hooks/llm-output.js";
import { handlePromptBuild } from "./hooks/prompt-build.js";
import { handleSessionStart } from "./hooks/session-start.js";

/** Shared context cache — 60s TTL, invalidated on session start. */
export const contextCache = new TTLCache<string>(60_000);

/** Tracks the last CLARKE query result for feedback submission. */
export const lastQueryResult = {
  requestId: "",
  query: "",
};

/**
 * Main plugin handler. OpenClaw calls this for every hook event.
 */
export default async function handler(event: any): Promise<any> {
  // agent:bootstrap — inject identity
  if (event.type === "agent" && event.action === "bootstrap") {
    return handleBootstrap(event);
  }

  // before_prompt_build — inject CLARKE session context into system prompt
  if (event.type === "before_prompt_build") {
    return handlePromptBuild(event);
  }

  // before_agent_reply — augment user query with retrieval-specific context
  if (event.type === "before_agent_reply") {
    return handleBeforeReply(event);
  }

  // session_start — greeting + cache invalidation
  if (event.type === "session_start") {
    return handleSessionStart(event);
  }

  // llm_output — feed back to CLARKE for learning (fire-and-forget)
  if (event.type === "llm_output") {
    return handleLlmOutput(event);
  }

  return undefined;
}
