/**
 * before_prompt_build hook — inject CLARKE context into every LLM call.
 *
 * This is the core integration point. Fires before every LLM call with
 * the system prompt already assembled. We append CLARKE's full context
 * pack (policies, decisions, skills, evidence, directives) so the model
 * sees it on every interaction — no file parsing needed.
 *
 * Uses a TTL cache (default 60s) to avoid hitting the CLARKE API on
 * every single call. Cache is invalidated on session start.
 */

import { fetchSessionContext, getClarkeConfig } from "../clarke-client.js";
import { contextCache } from "../index.js";

export async function handlePromptBuild(
  _event: any
): Promise<{ appendSystemContext: string } | undefined> {
  const config = getClarkeConfig();
  if (!config) return undefined;

  const context = await contextCache.getOrFetch(() =>
    fetchSessionContext(config)
  );

  if (context) {
    return {
      appendSystemContext: `\n\n<!-- CLARKE Context (auto-injected) -->\n${context}\n<!-- /CLARKE Context -->`,
    };
  }

  return undefined;
}
