"""Schemas for dynamic agent session context (Phase 7)."""

from pydantic import BaseModel, Field

from clarke.api.schemas.retrieval import ContextBudget
from clarke.utils.ids import generate_request_id


class AgentIdentity(BaseModel):
    name: str
    slug: str
    model_id: str
    capabilities: list[str] = []


class SkillEntry(BaseModel):
    skill_name: str
    content: str
    trigger_conditions: list[str] = []
    priority: int = 1
    score: float = 0.0
    effectiveness: float = 0.5


class SessionConstraints(BaseModel):
    budget_tokens: int
    allowed_sources: list[str] | None = None
    tool_access: list[str] = []


class SessionContextPack(BaseModel):
    identity: AgentIdentity
    directives: list[str] = []
    system_prompt: str
    policies: list[str] = []
    skills: list[SkillEntry] = []
    evidence: list[dict] = []
    decisions: list[dict] = []
    recent_state: list[dict] = []
    constraints: SessionConstraints
    budget: ContextBudget = ContextBudget()
    session_context_id: str
    degraded_mode: bool = False


class BuildSessionContextRequest(BaseModel):
    tenant_id: str
    project_id: str
    agent_profile_id: str | None = None
    agent_slug: str | None = None
    session_id: str = Field(default_factory=generate_request_id)
    task_context: str | None = None
    budget_tokens_override: int | None = None
    capabilities_override: list[str] | None = None
    format: str = "json"  # "json" | "markdown"


class CreateAgentProfileRequest(BaseModel):
    tenant_id: str
    project_id: str
    name: str
    slug: str
    model_id: str
    system_prompt_override: str | None = None
    behavioral_directives: list[str] = []
    capabilities: list[str] = []
    tool_access: list[str] = []
    budget_tokens: int = 8000
    allowed_sources: list[str] | None = None


class UpdateAgentProfileRequest(BaseModel):
    name: str | None = None
    model_id: str | None = None
    system_prompt_override: str | None = None
    behavioral_directives: list[str] | None = None
    capabilities: list[str] | None = None
    tool_access: list[str] | None = None
    budget_tokens: int | None = None
    allowed_sources: list[str] | None = None


class AgentProfileResponse(BaseModel):
    id: str
    tenant_id: str
    project_id: str
    name: str
    slug: str
    model_id: str
    capabilities: list[str] = []
    tool_access: list[str] = []
    budget_tokens: int = 8000
    status: str = "active"
    version: int = 1


class IngestSkillRequest(BaseModel):
    tenant_id: str
    project_id: str
    skill_name: str
    content: str
    trigger_conditions: list[str] = []
    tool_access: list[str] = []
    agent_capabilities: list[str] = []
    priority: int = 1
