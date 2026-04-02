/**
 * CLARKE plugin for OpenClaw.
 *
 * Registers as a **context engine** — the official OpenClaw mechanism for
 * controlling what the model sees on every call. This replaces the hook-based
 * approach which wasn't firing.
 *
 * The context engine:
 * - assemble(): Injects CLARKE context via systemPromptAddition on every LLM call
 * - ingest(): Captures every message for CLARKE's learning loop
 *
 * Also registers tools and slash commands for direct CLARKE interaction.
 */

import { TTLCache } from "./cache.js";
import {
  ensureRegistered,
  fetchGreeting,
  fetchHealth,
  fetchSessionContext,
  getClarkeConfig,
  listAgents,
  listPolicies,
  queryBroker,
  setConfig,
  submitFeedback,
} from "./clarke-client.js";

/** Shared context cache — 60s TTL. */
export const contextCache = new TTLCache<string>(60_000);

/** Tracks the last CLARKE query result for feedback submission. */
export const lastQueryResult = {
  requestId: "",
  query: "",
};

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

    // ── Memory Prompt Section ─────────────────────────────────────
    // Injects CLARKE memory context into the prompt alongside OpenClaw's
    // built-in memory. Called on every prompt build. Returns string[] that
    // OpenClaw adds to the system prompt.

    api.registerMemoryPromptSection((_params: any) => {
      const config = getClarkeConfig();
      if (!config?.tenantId) return [];

      // Use cached session context (populated by context engine's assemble)
      const cached = contextCache.get();
      if (!cached) return [];

      return [
        "## CLARKE Memory Context",
        "The following context is from CLARKE's brokered memory system.",
        "Policies and decisions are authoritative. Cite sources when referencing.",
        "",
        cached,
      ];
    });

    // ── Memory Runtime ──────────────────────────────────────────
    // Makes CLARKE available as a searchable memory backend.
    // OpenClaw's memory_search tool will route through CLARKE.

    api.registerMemoryRuntime({
      async getMemorySearchManager(params: any) {
        const config = getClarkeConfig();
        if (!config?.tenantId) return { manager: null, error: "CLARKE not configured" };

        return {
          manager: {
            status() {
              return {
                backend: "builtin" as const,
                provider: "clarke",
                workspaceDir: config.workspace,
              };
            },
            async probeEmbeddingAvailability() {
              const health = await fetchHealth(config);
              return { ok: !!health };
            },
            async probeVectorAvailability() {
              const health = await fetchHealth(config);
              return !!health;
            },
          },
        };
      },
      resolveMemoryBackendConfig(params: any) {
        return {
          backend: "builtin" as any,
          provider: "clarke",
        };
      },
    });

    // ── Context Engine ────────────────────────────────────────────
    // Handles per-query RAG augmentation and systemPromptAddition.
    // The assemble() method fetches CLARKE context (cached) and
    // query-specific retrieval results.

    api.registerContextEngine("clarke", () => ({
      info: {
        id: "clarke",
        name: "CLARKE Context Engine",
        ownsCompaction: false, // Let OpenClaw handle compaction
      },

      async ingest(params: any) {
        // Capture messages for CLARKE's learning loop
        const config = getClarkeConfig();
        if (!config?.tenantId) return { ingested: false };

        const content = params.message?.content || params.message?.text || "";
        const role = params.message?.role || "unknown";

        // If this is an assistant response and we have a pending query,
        // submit implicit positive feedback
        if (role === "assistant" && lastQueryResult.requestId) {
          submitFeedback(
            config,
            lastQueryResult.requestId,
            true,
            "Implicit positive — agent responded without correction."
          ).catch(() => {});
          lastQueryResult.requestId = "";
          lastQueryResult.query = "";
        }

        return { ingested: true };
      },

      async assemble(params: any) {
        const config = getClarkeConfig();
        if (!config) {
          return {
            messages: params.messages || [],
            estimatedTokens: 0,
          };
        }

        // Ensure registered on first assemble
        await ensureRegistered(config);

        // Fetch CLARKE session context (cached 60s)
        const sessionContext = await contextCache.getOrFetch(() =>
          fetchSessionContext(config)
        );

        // Query-augment: if the last user message is new, run it through the broker
        let queryContext = "";
        const messages = params.messages || [];
        const lastUserMsg = [...messages]
          .reverse()
          .find((m: any) => m.role === "user");
        const userContent = lastUserMsg?.content || "";

        if (
          userContent &&
          userContent.length > 5 &&
          !userContent.startsWith("/")
        ) {
          const result = await queryBroker(config, userContent);
          if (result?.answer) {
            lastQueryResult.requestId = result.requestId;
            lastQueryResult.query = userContent;
            queryContext = `\n\n## CLARKE Query Context\n${result.answer}`;
            if (result.degradedMode) {
              queryContext +=
                "\n*(degraded mode — some retrieval sources unavailable)*";
            }
          }
        }

        // Build the system prompt addition
        const parts: string[] = [];
        if (sessionContext) {
          parts.push(sessionContext);
        }
        if (queryContext) {
          parts.push(queryContext);
        }

        return {
          messages: params.messages || [],
          estimatedTokens: params.estimatedTokens || 0,
          systemPromptAddition: parts.length > 0 ? parts.join("\n") : undefined,
        };
      },

      async compact(params: any) {
        // Invalidate cache on compaction so next assemble gets fresh context
        contextCache.invalidate();
        return { ok: true, compacted: false };
      },
    }));

    // ── Tools ─────────────────────────────────────────────────────

    api.registerTool(() => ({
      name: "clarke_status",
      description: "Check CLARKE system health, list agents and policies",
      inputSchema: { type: "object" as const, properties: {} },
      async execute() {
        const config = getClarkeConfig();
        if (!config)
          return { content: [{ type: "text" as const, text: "CLARKE not configured." }] };
        await ensureRegistered(config);
        const health = await fetchHealth(config);
        if (!health)
          return { content: [{ type: "text" as const, text: "CLARKE is offline." }] };
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
        if (!config)
          return { content: [{ type: "text" as const, text: "CLARKE not configured." }] };
        await ensureRegistered(config);
        const result = await queryBroker(config, params.question);
        if (!result)
          return { content: [{ type: "text" as const, text: "Query failed." }] };
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
        if (!config)
          return { content: [{ type: "text" as const, text: "CLARKE not configured." }] };
        await ensureRegistered(config);
        const result = await queryBroker(config, `Remember this: ${params.content}`);
        if (!result)
          return { content: [{ type: "text" as const, text: "Failed." }] };
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
        if (!config)
          return { content: [{ type: "text" as const, text: "CLARKE not configured." }] };
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
          } catch {
            continue;
          }
        }
        const text = total === 0 ? "No pending proposals." : `${total} pending:\n${lines.join("\n")}`;
        return { content: [{ type: "text" as const, text }] };
      },
    }));

    // ── Slash Commands ────────────────────────────────────────────

    api.registerCommand({
      name: "clarke",
      description: "CLARKE dashboard",
      async handler() {
        const config = getClarkeConfig();
        if (!config) return { text: "CLARKE not configured." };
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
