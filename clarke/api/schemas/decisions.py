"""Decision management schemas."""

from pydantic import BaseModel


class CreateDecisionRequest(BaseModel):
    tenant_id: str
    project_id: str
    title: str
    rationale: str
    decided_by: str
    alternatives: list[dict] | None = None


class DecisionResponse(BaseModel):
    id: str
    title: str
    status: str


class DecisionListItem(BaseModel):
    id: str
    title: str
    rationale: str
    status: str
    decided_at: str
