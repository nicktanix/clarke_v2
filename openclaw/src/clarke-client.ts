/**
 * CLARKE API client for the OpenClaw plugin.
 *
 * Uses native fetch() — no dependencies. Reads config from environment
 * variables or plugin configuration.
 */

export interface ClarkeConfig {
  endpoint: string;
  tenantId: string;
  projectId: string;
  agentSlug: string;
  workspace: string;
}

let _config: ClarkeConfig | null = null;

/**
 * Resolve CLARKE config from environment variables.
 *
 * If CLARKE_TENANT_ID and CLARKE_PROJECT_ID are set, uses them directly.
 * Otherwise, auto-registers with the CLARKE backend using the workspace
 * path to derive a project name (each workspace gets its own CLARKE project).
 */
export function resolveConfig(): ClarkeConfig | null {
  const endpoint =
    process.env.CLARKE_API_URL || process.env.CLARKE_ENDPOINT || "";
  const agentSlug = process.env.CLARKE_AGENT_SLUG || "clarke-operator";
  const workspace = process.env.OPENCLAW_WORKSPACE || process.cwd();

  if (!endpoint) return null;

  let tenantId = process.env.CLARKE_TENANT_ID || "";
  let projectId = process.env.CLARKE_PROJECT_ID || "";

  // If IDs are pre-configured, use them
  if (tenantId && projectId) {
    return { endpoint, tenantId, projectId, agentSlug, workspace };
  }

  // Otherwise, we'll auto-register on first use (see ensureRegistered)
  return { endpoint, tenantId, projectId, agentSlug, workspace };
}

/**
 * Get or create the singleton CLARKE config.
 */
export function getClarkeConfig(): ClarkeConfig | null {
  if (!_config) {
    _config = resolveConfig();
  }
  return _config;
}

/**
 * Auto-register this workspace with CLARKE if tenant/project IDs aren't set.
 *
 * Calls POST /admin/setup with the workspace path as the project name.
 * The endpoint is idempotent — same workspace path always returns the same IDs.
 */
export async function ensureRegistered(
  config: ClarkeConfig
): Promise<ClarkeConfig> {
  if (config.tenantId && config.projectId) return config;

  try {
    // Derive a project name from the workspace path
    const projectName = `openclaw:${config.workspace.replace(/\//g, ":")}`;

    const resp = await fetch(`${config.endpoint}/admin/setup`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        tenant_name: "openclaw",
        project_name: projectName,
      }),
      signal: AbortSignal.timeout(10_000),
    });

    if (resp.ok) {
      const data = (await resp.json()) as {
        tenant_id: string;
        project_id: string;
      };
      config.tenantId = data.tenant_id;
      config.projectId = data.project_id;
    }
  } catch {
    // Non-fatal — config will have empty IDs, API calls will fail gracefully
  }

  return config;
}

/**
 * Fetch CLARKE session context as rendered markdown.
 */
export async function fetchSessionContext(
  config: ClarkeConfig
): Promise<string | null> {
  try {
    const resp = await fetch(`${config.endpoint}/agents/session-context`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        tenant_id: config.tenantId,
        project_id: config.projectId,
        agent_slug: config.agentSlug,
        format: "markdown",
      }),
      signal: AbortSignal.timeout(15_000),
    });

    if (!resp.ok) return null;
    return await resp.text();
  } catch {
    return null;
  }
}

/**
 * Fetch CLARKE health status.
 */
export async function fetchHealth(
  config: ClarkeConfig
): Promise<{ status: string; version: string } | null> {
  try {
    const resp = await fetch(`${config.endpoint}/health`, {
      signal: AbortSignal.timeout(5_000),
    });
    if (!resp.ok) return null;
    return (await resp.json()) as { status: string; version: string };
  } catch {
    return null;
  }
}

/**
 * List agent profiles for the tenant.
 */
export async function listAgents(config: ClarkeConfig): Promise<any[]> {
  try {
    const url = new URL(`${config.endpoint}/agents/profiles`);
    url.searchParams.set("tenant_id", config.tenantId);
    url.searchParams.set("status", "active");
    const resp = await fetch(url.toString(), {
      signal: AbortSignal.timeout(5_000),
    });
    if (!resp.ok) return [];
    return (await resp.json()) as any[];
  } catch {
    return [];
  }
}

/**
 * List active policies for the tenant.
 */
export async function listPolicies(config: ClarkeConfig): Promise<any[]> {
  try {
    const url = new URL(`${config.endpoint}/policy`);
    url.searchParams.set("tenant_id", config.tenantId);
    const resp = await fetch(url.toString(), {
      signal: AbortSignal.timeout(5_000),
    });
    if (!resp.ok) return [];
    return (await resp.json()) as any[];
  } catch {
    return [];
  }
}

/**
 * Send a query through the CLARKE broker for retrieval-augmented context.
 *
 * Returns the broker's answer (which includes grounded context from
 * policies, decisions, docs, and episodic memory) plus the request_id
 * for feedback submission.
 */
export async function queryBroker(
  config: ClarkeConfig,
  message: string,
  sessionId?: string
): Promise<{ answer: string; requestId: string; degradedMode: boolean } | null> {
  try {
    const resp = await fetch(`${config.endpoint}/query`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        tenant_id: config.tenantId,
        project_id: config.projectId,
        user_id: "openclaw-agent",
        message,
        session_id: sessionId,
      }),
      signal: AbortSignal.timeout(30_000),
    });
    if (!resp.ok) return null;
    const data = (await resp.json()) as any;
    return {
      answer: data.answer || "",
      requestId: data.request_id || "",
      degradedMode: data.degraded_mode || false,
    };
  } catch {
    return null;
  }
}

/**
 * Submit feedback on a CLARKE query response.
 */
export async function submitFeedback(
  config: ClarkeConfig,
  requestId: string,
  accepted: boolean,
  notes?: string
): Promise<void> {
  try {
    await fetch(`${config.endpoint}/feedback`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        request_id: requestId,
        tenant_id: config.tenantId,
        user_id: "openclaw-agent",
        accepted,
        notes,
      }),
      signal: AbortSignal.timeout(5_000),
    });
  } catch {
    // Best-effort, don't fail the interaction
  }
}

/**
 * Build a concise greeting string for session start.
 */
export async function fetchGreeting(config: ClarkeConfig): Promise<string> {
  const health = await fetchHealth(config);
  if (!health) {
    return "CLARKE is offline | start with: make dev";
  }

  const agents = await listAgents(config);
  const policies = await listPolicies(config);

  const parts: string[] = [`CLARKE is ${health.status}`];

  const stats: string[] = [];
  if (agents.length > 0) {
    stats.push(`${agents.length} agent${agents.length !== 1 ? "s" : ""}`);
  }
  if (policies.length > 0) {
    stats.push(
      `${policies.length} ${policies.length !== 1 ? "policies" : "policy"}`
    );
  }
  if (stats.length > 0) {
    parts.push(stats.join(", "));
  }

  parts.push("/clarke for dashboard");
  return parts.join(" | ");
}
