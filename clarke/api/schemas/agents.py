"""Agent-related schemas."""

from typing import Literal

from pydantic import BaseModel


class SubagentSpawnRequest(BaseModel):
    type: Literal["SUBAGENT_SPAWN"] = "SUBAGENT_SPAWN"
    task: str
    capabilities: list[str] = []
    required_memory: list[str] = []
    handoff_evidence: list[str] = []
    max_depth: int = 3
    timeout_minutes: int = 30
    memory_scope_mode: str = "hybrid"
    budget_tokens: int | None = None


class SubagentResult(BaseModel):
    type: Literal["SUBAGENT_RESULT"] = "SUBAGENT_RESULT"
    subagent_handle: str
    status: str
    summary: str
    evidence: list[str] = []
    artifacts: list[dict] = []
    open_questions: list[str] = []


class SpawnResponse(BaseModel):
    subagent_handle: str
    query_url: str
    expires_at: str


class AgentStatusResponse(BaseModel):
    id: str
    tenant_id: str
    task_definition: str
    depth: int
    status: str
    created_at: str
    expires_at: str | None


class IngestResultRequest(BaseModel):
    status: str = "completed"
    summary: str
    evidence_item_ids: list[str] = []
    artifact_refs: list[dict] = []
    open_questions: list[str] = []


class CancelAgentRequest(BaseModel):
    reason: str = "cancelled by parent"
