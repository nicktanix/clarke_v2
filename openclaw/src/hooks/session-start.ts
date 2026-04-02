/**
 * session_start hook — CLARKE greeting and cache invalidation.
 *
 * Fires when a new session begins. Invalidates the context cache so the
 * next LLM call gets fresh context, and outputs a status greeting.
 */

import { fetchGreeting, getClarkeConfig } from "../clarke-client.js";
import { contextCache } from "../index.js";

export async function handleSessionStart(event: any): Promise<void> {
  // Always invalidate cache on session start — force fresh context
  contextCache.invalidate();

  const config = getClarkeConfig();
  if (!config) return;

  const greeting = await fetchGreeting(config);

  // Push greeting into session messages for the user to see
  if (event.messages && Array.isArray(event.messages)) {
    event.messages.push(greeting);
  }
}
