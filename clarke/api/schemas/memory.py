"""Schemas for the memory assessment endpoint."""

from pydantic import BaseModel, Field


class MemoryAssessRequest(BaseModel):
    """A user/assistant turn to be assessed for memory storage."""

    tenant_id: str
    project_id: str
    user_id: str = "openclaw-agent"
    agent_slug: str | None = None
    session_id: str | None = None
    user_message: str = Field(..., min_length=1, max_length=10_000)
    assistant_message: str = Field(..., min_length=1, max_length=50_000)


class MemoryAssessResponse(BaseModel):
    """Classification result from turn assessment."""

    stored: bool
    memory_type: str
    significance_score: float
    reason: str
