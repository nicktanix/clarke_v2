"""Schemas for directive proposals (Phase 7b)."""

from pydantic import BaseModel


class DirectiveProposalResponse(BaseModel):
    id: str
    proposed_directive: str
    source_memory_ids: list[str] = []
    cluster_size: int = 0
    similarity_score: float = 0.0
    status: str = "pending_approval"
    proposed_at: str | None = None
    reviewed_by: str | None = None
    review_comment: str | None = None


class ApproveDirectiveRequest(BaseModel):
    approver_id: str
    comment: str | None = None


class RejectDirectiveRequest(BaseModel):
    approver_id: str
    comment: str | None = None
