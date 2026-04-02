/**
 * CLARKE API client for the OpenClaw plugin.
 *
 * Config is injected via setConfig() from the plugin register function,
 * using the pluginConfig API provided by the host.
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
 * Set config from the plugin register(api) call.
 * Called once during plugin initialization.
 */
export function setConfig(pluginConfig: Record<string, unknown>, workspaceDir: string): void {
  _config = {
    endpoint: (pluginConfig?.endpoint as string) || "http://localhost:8000",
    tenantId: (pluginConfig?.tenant_id as string) || "",
    projectId: (pluginConfig?.project_id as string) || "",
    agentSlug: (pluginConfig?.agent_slug as string) || "clarke-operator",
    workspace: workspaceDir || "",
  };
}

/**
 * Get the CLARKE config (must call setConfig first).
 */
export function getClarkeConfig(): ClarkeConfig | null {
  return _config;
}

/**
 * Auto-register this workspace with CLARKE if tenant/project IDs aren't set.
 */
export async function ensureRegistered(
  config: ClarkeConfig
): Promise<ClarkeConfig> {
  if (config.tenantId && config.projectId) return config;

  try {
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
    // Non-fatal
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
 * Send a query through the CLARKE broker.
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
    // Best-effort
  }
}

/**
 * Ingest a document or session transcript into CLARKE.
 */
export async function ingestDocument(
  config: ClarkeConfig,
  filename: string,
  content: string,
  metadata?: Record<string, unknown>
): Promise<boolean> {
  try {
    const resp = await fetch(`${config.endpoint}/ingest`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        tenant_id: config.tenantId,
        project_id: config.projectId,
        filename,
        content_type: "text/markdown",
        content,
        metadata: { source: "openclaw_session", ...metadata },
      }),
      signal: AbortSignal.timeout(30_000),
    });
    return resp.ok;
  } catch {
    return false;
  }
}

/**
 * Result from the memory assessment endpoint.
 */
export interface AssessResult {
  stored: boolean;
  memoryType: string;
  significanceScore: number;
  reason: string;
}

/**
 * Assess a user/assistant turn for memory significance.
 * CLARKE classifies the turn and stores it if worthy.
 * Returns the classification result so the caller can decide
 * whether to refresh context.
 */
export async function assessTurn(
  config: ClarkeConfig,
  userMessage: string,
  assistantMessage: string,
  sessionId?: string
): Promise<AssessResult | null> {
  try {
    const resp = await fetch(`${config.endpoint}/memory/assess`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        tenant_id: config.tenantId,
        project_id: config.projectId,
        user_id: "openclaw-agent",
        agent_slug: config.agentSlug,
        session_id: sessionId,
        user_message: userMessage,
        assistant_message: assistantMessage,
      }),
      signal: AbortSignal.timeout(15_000),
    });
    if (!resp.ok) return null;
    const data = (await resp.json()) as any;
    return {
      stored: data.stored,
      memoryType: data.memory_type,
      significanceScore: data.significance_score,
      reason: data.reason,
    };
  } catch {
    return null;
  }
}

/**
 * Build a concise greeting string.
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
