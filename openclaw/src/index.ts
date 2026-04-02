/**
 * CLARKE plugin for OpenClaw.
 *
 * Exports an OpenClawPluginDefinition that registers hooks, tools,
 * and slash commands through the official plugin API.
 */

import { TTLCache } from "./cache.js";
import {
  ensureRegistered,
  fetchGreeting,
  fetchHealth,
  getClarkeConfig,
  listAgents,
  listPolicies,
  queryBroker,
  setConfig,
  submitFeedback,
} from "./clarke-client.js";
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
 * OpenClaw plugin definition.
 * Exports an OpenClawPluginDefinition — no special wrapper needed.
 */
const clarkePlugin = {
  id: "clarke",
  name: "CLARKE",
  description:
    "Cognitive Learning Augmentation Retrieval Knowledge Engine — brokered memory and context management",

  register(api: any) {
    // ── Initialize config from OpenClaw plugin API ────────────────
    const pluginConfig = api.pluginConfig || {};
    const workspaceDir = api.config?.agents?.defaults?.workspace || "";
    setConfig(pluginConfig, workspaceDir);

    // ── Hooks ─────────────────────────────────────────────────────

    api.registerHook("agent:bootstrap", handleBootstrap);
    api.registerHook("before_prompt_build", handlePromptBuild);
    api.registerHook("before_agent_reply", handleBeforeReply);
    api.registerHook("session_start", handleSessionStart);
    api.registerHook("llm_output", handleLlmOutput);

    // ── Tools (agent-callable via tool use) ───────────────────────

    api.registerTool(() => ({
      name: "clarke_status",
      description: "Check CLARKE system health, list agents and policies",
      inputSchema: { type: "object" as const, properties: {} },
      async execute() {
        const config = getClarkeConfig();
        if (!config) return { content: [{ type: "text" as const, text: "CLARKE not configured." }] };
        await ensureRegistered(config);
        const health = await fetchHealth(config);
        if (!health) return { content: [{ type: "text" as const, text: "CLARKE is offline." }] };
        const agents = await listAgents(config);
        const policies = await listPolicies(config);
        const text = [
          `CLARKE: ${health.status} | v${health.version}`,
          `Agents: ${agents.length} | Policies: ${policies.length}`,
          ...agents.map((a: any) => `  ${a.name} (${a.slug})`),
        ].join("\n");
        return { content: [{ type: "text" as const, text }] };
      },
    }));

    api.registerTool(() => ({
      name: "clarke_recall",
      description: "Query CLARKE memory for retrieval-augmented answers",
      inputSchema: {
        type: "object" as const,
        properties: { question: { type: "string", description: "What to ask" } },
        required: ["question"],
      },
      async execute(_id: string, params: any) {
        const config = getClarkeConfig();
        if (!config) return { content: [{ type: "text" as const, text: "CLARKE not configured." }] };
        await ensureRegistered(config);
        const result = await queryBroker(config, params.question);
        if (!result) return { content: [{ type: "text" as const, text: "Query failed." }] };
        return { content: [{ type: "text" as const, text: result.answer }] };
      },
    }));

    api.registerTool(() => ({
      name: "clarke_teach",
      description: "Submit knowledge, corrections, or decisions to CLARKE",
      inputSchema: {
        type: "object" as const,
        properties: { content: { type: "string", description: "What to teach" } },
        required: ["content"],
      },
      async execute(_id: string, params: any) {
        const config = getClarkeConfig();
        if (!config) return { content: [{ type: "text" as const, text: "CLARKE not configured." }] };
        await ensureRegistered(config);
        const result = await queryBroker(config, `Remember this: ${params.content}`);
        if (!result) return { content: [{ type: "text" as const, text: "Failed." }] };
        await submitFeedback(config, result.requestId, true, `Teaching: ${params.content}`);
        return { content: [{ type: "text" as const, text: "Recorded." }] };
      },
    }));

    api.registerTool(() => ({
      name: "clarke_review",
      description: "List pending CLARKE directive proposals",
      inputSchema: { type: "object" as const, properties: {} },
      async execute() {
        const config = getClarkeConfig();
        if (!config) return { content: [{ type: "text" as const, text: "CLARKE not configured." }] };
        await ensureRegistered(config);
        const agents = await listAgents(config);
        const lines: string[] = [];
        let total = 0;
        for (const agent of agents) {
          try {
            const url = new URL(`${config.endpoint}/agents/profiles/${agent.id}/directives/proposals`);
            url.searchParams.set("status", "pending_approval");
            const resp = await fetch(url.toString(), { signal: AbortSignal.timeout(5_000) });
            if (!resp.ok) continue;
            const proposals = (await resp.json()) as any[];
            for (const p of proposals) {
              total++;
              lines.push(`${total}. "${p.proposed_directive}" (${p.cluster_size} corrections)`);
            }
          } catch { continue; }
        }
        const text = total === 0 ? "No pending proposals." : `${total} pending:\n${lines.join("\n")}`;
        return { content: [{ type: "text" as const, text }] };
      },
    }));

    // ── Slash Commands (deterministic, no LLM) ────────────────────

    api.registerCommand({
      name: "clarke",
      description: "CLARKE dashboard",
      async handler() {
        const config = getClarkeConfig();
        if (!config) return { text: "CLARKE not configured. Set CLARKE_API_URL." };
        await ensureRegistered(config);
        return { text: await fetchGreeting(config) };
      },
    });

    api.registerCommand({
      name: "clarke_recall",
      description: "Query CLARKE memory",
      acceptsArgs: true,
      async handler(ctx: any) {
        const q = ctx.args?.trim();
        if (!q) return { text: "Usage: /clarke_recall <question>" };
        const config = getClarkeConfig();
        if (!config) return { text: "CLARKE not configured." };
        await ensureRegistered(config);
        const result = await queryBroker(config, q);
        return { text: result?.answer || "Query failed." };
      },
    });

    api.registerCommand({
      name: "clarke_teach",
      description: "Teach CLARKE something",
      acceptsArgs: true,
      async handler(ctx: any) {
        const note = ctx.args?.trim();
        if (!note) return { text: "Usage: /clarke_teach <what to remember>" };
        const config = getClarkeConfig();
        if (!config) return { text: "CLARKE not configured." };
        await ensureRegistered(config);
        const result = await queryBroker(config, `Remember this: ${note}`);
        if (!result) return { text: "Failed." };
        await submitFeedback(config, result.requestId, true, `Teaching: ${note}`);
        return { text: "Recorded." };
      },
    });
  },
};

export default clarkePlugin;
