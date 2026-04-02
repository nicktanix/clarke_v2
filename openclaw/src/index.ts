/**
 * CLARKE plugin for OpenClaw.
 *
 * Registers:
 * - Hooks: context injection, query augmentation, learning feedback
 * - Slash commands: /clarke, /clarke-teach, /clarke-recall, /clarke-review, etc.
 * - Skills: bundled SKILL.md files in the skills/ directory
 *
 * The plugin uses definePluginEntry so OpenClaw discovers it properly
 * from the openclaw.plugin.json manifest.
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
 * Plugin entry point using OpenClaw's definePluginEntry pattern.
 */
export default {
  id: "clarke",
  name: "CLARKE",
  description:
    "Cognitive Learning Augmentation Retrieval Knowledge Engine — brokered memory and context management",

  register(api: any) {
    // ── Hooks ─────────────────────────────────────────────────────

    api.registerHook?.("agent:bootstrap", handleBootstrap);
    api.registerHook?.("before_prompt_build", handlePromptBuild);
    api.registerHook?.("before_agent_reply", handleBeforeReply);
    api.registerHook?.("session_start", handleSessionStart);
    api.registerHook?.("llm_output", handleLlmOutput);

    // ── Slash Commands ────────────────────────────────────────────
    // These run deterministically (no LLM) for fast status checks
    // and direct API interactions.

    api.registerCommand?.({
      name: "clarke",
      description: "CLARKE dashboard — system health, agents, policies",
      handler: async () => {
        const config = getClarkeConfig();
        if (!config) return { text: "CLARKE not configured. Set CLARKE_API_URL." };
        await ensureRegistered(config);

        const health = await fetchHealth(config);
        if (!health) return { text: "CLARKE is offline. Start with: make dev" };

        const agents = await listAgents(config);
        const policies = await listPolicies(config);

        const lines = [
          "CLARKE Command Center",
          "=====================",
          "",
          `System: ${health.status} | v${health.version}`,
          "",
          `Agents (${agents.length}):`,
          ...agents.map(
            (a: any) => `  ${a.name} (${a.slug}) — ${(a.capabilities || []).join(", ")}`
          ),
          ...(agents.length === 0 ? ["  (none — use /clarke-agent to create one)"] : []),
          "",
          `Policies (${policies.length}):`,
          ...policies.map((p: any) => `  ${p.content?.substring(0, 80) || "(empty)"}`),
          ...(policies.length === 0 ? ["  (none — use /clarke-teach to add one)"] : []),
          "",
          "Commands:",
          "  /clarke          this dashboard",
          "  /clarke-recall   query CLARKE memory",
          "  /clarke-teach    record decisions, policies, corrections",
          "  /clarke-review   approve directive proposals",
          "  /clarke-status   quick health check",
        ];
        return { text: lines.join("\n") };
      },
    });

    api.registerCommand?.({
      name: "clarke_status",
      description: "Quick CLARKE health check",
      handler: async () => {
        const config = getClarkeConfig();
        if (!config) return { text: "CLARKE not configured." };
        const greeting = await fetchGreeting(config);
        return { text: greeting };
      },
    });

    api.registerCommand?.({
      name: "clarke_recall",
      description: "Query CLARKE memory",
      acceptsArgs: true,
      handler: async (ctx: any) => {
        const query = ctx.args?.trim();
        if (!query) return { text: "Usage: /clarke-recall <question>" };

        const config = getClarkeConfig();
        if (!config) return { text: "CLARKE not configured." };
        await ensureRegistered(config);

        const result = await queryBroker(config, query);
        if (!result) return { text: "CLARKE query failed — is the server running?" };

        const lines = [
          "CLARKE Recall",
          "=============",
          "",
          result.answer,
          "",
          `Trace: ${result.requestId}`,
          result.degradedMode ? "(degraded mode — some sources unavailable)" : "",
        ].filter(Boolean);
        return { text: lines.join("\n") };
      },
    });

    api.registerCommand?.({
      name: "clarke_teach",
      description: "Submit feedback or correction to CLARKE",
      acceptsArgs: true,
      handler: async (ctx: any) => {
        const note = ctx.args?.trim();
        if (!note) {
          return {
            text: [
              "Usage: /clarke-teach <what to remember>",
              "",
              "Examples:",
              '  /clarke-teach we decided to use structlog for all logging',
              '  /clarke-teach correction: always use pytest, not unittest',
              '  /clarke-teach policy: all endpoints must validate tenant_id',
            ].join("\n"),
          };
        }

        const config = getClarkeConfig();
        if (!config) return { text: "CLARKE not configured." };
        await ensureRegistered(config);

        // Route to the broker as a query — CLARKE's episodic memory
        // will store this as a high-significance interaction
        const result = await queryBroker(config, `Remember this: ${note}`);
        if (!result) return { text: "Failed to reach CLARKE." };

        // Submit as positive feedback to reinforce
        await submitFeedback(config, result.requestId, true, `User teaching: ${note}`);

        return { text: `Recorded. CLARKE will reference this in future interactions.` };
      },
    });

    api.registerCommand?.({
      name: "clarke_review",
      description: "List pending directive proposals for review",
      handler: async () => {
        const config = getClarkeConfig();
        if (!config) return { text: "CLARKE not configured." };
        await ensureRegistered(config);

        const agents = await listAgents(config);
        if (agents.length === 0) return { text: "No agents registered." };

        const lines = ["CLARKE Review Queue", "===================", ""];

        let total = 0;
        for (const agent of agents) {
          try {
            const url = new URL(
              `${config.endpoint}/agents/profiles/${agent.id}/directives/proposals`
            );
            url.searchParams.set("status", "pending_approval");
            const resp = await fetch(url.toString(), {
              signal: AbortSignal.timeout(5_000),
            });
            if (!resp.ok) continue;
            const proposals = (await resp.json()) as any[];
            if (proposals.length === 0) continue;

            lines.push(`Agent: ${agent.name} (${agent.slug})`);
            for (const p of proposals) {
              total++;
              lines.push(`  ${total}. "${p.proposed_directive}"`);
              lines.push(`     Cluster: ${p.cluster_size} corrections | Similarity: ${p.similarity_score}`);
            }
            lines.push("");
          } catch {
            continue;
          }
        }

        if (total === 0) {
          lines.push("No pending proposals. System is up to date.");
        } else {
          lines.push(`${total} proposal(s) need review.`);
          lines.push("Use the clarke_approve_directive or clarke_reject_directive MCP tools to act.");
        }

        return { text: lines.join("\n") };
      },
    });
  },
};
