/**
 * CLARKE plugin for OpenClaw — native context injection.
 *
 * Hooks into OpenClaw's plugin system to programmatically inject CLARKE
 * context into every LLM call via before_prompt_build. No file writing,
 * no markdown parsing — context goes directly into the system prompt.
 *
 * Hook events handled:
 * - agent:bootstrap     — inject CLARKE identity into bootstrap files
 * - before_prompt_build — inject live CLARKE context (cached, 60s TTL)
 * - session_start       — invalidate cache, output greeting
 */

import { TTLCache } from "./cache.js";
import { handleBootstrap } from "./hooks/bootstrap.js";
import { handlePromptBuild } from "./hooks/prompt-build.js";
import { handleSessionStart } from "./hooks/session-start.js";

/** Shared context cache — 60s TTL, invalidated on session start. */
export const contextCache = new TTLCache<string>(60_000);

/**
 * Main plugin handler. OpenClaw calls this for every hook event.
 */
export default async function handler(event: any): Promise<any> {
  // agent:bootstrap — inject identity
  if (event.type === "agent" && event.action === "bootstrap") {
    return handleBootstrap(event);
  }

  // before_prompt_build — inject CLARKE context into system prompt
  if (event.type === "before_prompt_build") {
    return handlePromptBuild(event);
  }

  // session_start — greeting + cache invalidation
  if (event.type === "session_start") {
    return handleSessionStart(event);
  }

  return undefined;
}
