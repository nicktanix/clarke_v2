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
}

let _config: ClarkeConfig | null = null;

/**
 * Resolve CLARKE config from environment variables.
 */
export function resolveConfig(): ClarkeConfig | null {
  const endpoint =
    process.env.CLARKE_API_URL || process.env.CLARKE_ENDPOINT || "";
  const tenantId = process.env.CLARKE_TENANT_ID || "";
  const projectId = process.env.CLARKE_PROJECT_ID || "";
  const agentSlug = process.env.CLARKE_AGENT_SLUG || "clarke-operator";

  if (!endpoint || !tenantId || !projectId) {
    return null;
  }

  return { endpoint, tenantId, projectId, agentSlug };
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
