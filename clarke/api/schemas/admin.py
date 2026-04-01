"""Admin API schemas for proto-class management."""

from pydantic import BaseModel


class ProtoClassListItem(BaseModel):
    id: str
    label: str | None
    member_count: int
    stability_score: float
    status: str


class ProtoClassAction(BaseModel):
    target_id: str | None = None


class ClusterRequest(BaseModel):
    tenant_id: str


class ClusterResponse(BaseModel):
    clusters_created: int
    classes: list[dict]
