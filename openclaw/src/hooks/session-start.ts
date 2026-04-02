/**
 * session_start hook — auto-register workspace, greeting, cache invalidation.
 *
 * Fires when a new session begins. If the workspace hasn't been registered
 * with CLARKE yet (no TENANT_ID/PROJECT_ID env vars), auto-registers it
 * using the workspace path as the project key. Then invalidates the context
 * cache and outputs a greeting.
 */

import {
  ensureRegistered,
  fetchGreeting,
  getClarkeConfig,
} from "../clarke-client.js";
import { contextCache } from "../index.js";

export async function handleSessionStart(event: any): Promise<void> {
  // Always invalidate cache on session start — force fresh context
  contextCache.invalidate();

  const config = getClarkeConfig();
  if (!config) return;

  // Auto-register this workspace if not already configured
  await ensureRegistered(config);

  if (!config.tenantId || !config.projectId) {
    // Registration failed — still output a greeting
    event.messages?.push("CLARKE is offline | start with: make dev");
    return;
  }

  const greeting = await fetchGreeting(config);

  if (event.messages && Array.isArray(event.messages)) {
    event.messages.push(greeting);
  }
}
