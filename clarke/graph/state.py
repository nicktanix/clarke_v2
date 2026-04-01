"""LangGraph broker state definition."""

from typing import TypedDict


class BrokerState(TypedDict, total=False):
    # Request identity
    request_id: str
    tenant_id: str
    project_id: str
    user_id: str
    session_id: str | None
    message: str

    # Agent context (Phase 6, stubbed)
    agent_id: str | None
    root_agent_id: str | None
    parent_agent_id: str | None
    agent_depth: int

    # Execution state
    query_features: dict | None
    retrieval_plan: list[dict]
    retrieved_items: list[dict]
    injected_items: list[dict]
    context_pack: dict | None

    # Model interaction
    prompt_version_id: str
    context_template_version_id: str
    model_response: str | None
    structured_output: dict | None

    # Health and mode
    degraded_mode: bool
    execution_mode: str  # "full", "reduced", "canonical_only"
    health_status: dict

    # Escalation flags
    context_request_detected: bool
    subagent_spawn_requested: bool
    subagent_spawn_approved: bool

    # CONTEXT_REQUEST loop (Phase 3)
    context_request: dict | None
    retrieval_loop_count: int
    second_pass_retrieved_items: list[dict]
    second_pass_injected_items: list[dict]
    second_pass_context_pack: dict | None

    # Attribution (Phase 3)
    answer_attributions: list[dict]
    useful_context_ratio: float | None
    episode_id: str | None

    # Graph memory (Phase 4)
    graph_retrieved_items: list[dict]
    policy_items: list[dict]
    decision_items: list[dict]
    graph_health: bool

    # Sub-agent spawn (Phase 6)
    spawn_request: dict | None
    subagent_handle: str | None
    subagent_instance_id: str | None

    # Output
    answer: str | None
    error: str | None
    latency_ms: int | None
