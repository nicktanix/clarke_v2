/**
 * before_agent_reply hook — augment user queries with CLARKE retrieval.
 *
 * Fires after the user message is received but before the LLM runs.
 * Sends the user's message through CLARKE's broker which performs
 * semantic search, reranking, and context composition against the
 * user's specific query. The retrieved context is appended to the
 * system prompt so the LLM has both:
 *   1. Session-level context (from before_prompt_build — policies, skills, etc.)
 *   2. Query-specific context (from this hook — relevant docs, decisions, memory)
 *
 * This is the RAG layer — it makes every user message retrieval-augmented.
 */

import { getClarkeConfig, queryBroker } from "../clarke-client.js";
import { lastQueryResult } from "../index.js";

export async function handleBeforeReply(
  event: any
): Promise<{ appendSystemContext: string } | undefined> {
  const config = getClarkeConfig();
  if (!config) return undefined;

  // Extract the user's message from the event
  const userMessage = event.message?.content || event.message?.text || "";
  if (!userMessage || userMessage.length < 5) return undefined;

  // Skip CLARKE queries for slash commands (handled by skills/MCP)
  if (userMessage.startsWith("/clarke")) return undefined;

  // Query the CLARKE broker for retrieval-augmented context
  const result = await queryBroker(config, userMessage, event.sessionId);
  if (!result || !result.answer) return undefined;

  // Store the result so llm_output can submit feedback
  lastQueryResult.requestId = result.requestId;
  lastQueryResult.query = userMessage;

  // Build the augmented context block
  const augmented = [
    "\n\n<!-- CLARKE Query Context (retrieval-augmented) -->",
    `The CLARKE broker retrieved the following context for this specific query.`,
    `Use this alongside the session context above. Cite sources when referencing.`,
    "",
    result.answer,
    result.degradedMode
      ? "\n*Note: CLARKE is in degraded mode — some retrieval sources were unavailable.*"
      : "",
    "<!-- /CLARKE Query Context -->",
  ]
    .filter(Boolean)
    .join("\n");

  return { appendSystemContext: augmented };
}
