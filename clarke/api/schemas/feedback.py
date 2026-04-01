"""Feedback schemas."""

from pydantic import BaseModel


class FeedbackRequest(BaseModel):
    request_id: str
    tenant_id: str
    user_id: str
    accepted: bool
    score: float | None = None
    retrieved_item_ids: list[str] = []
    notes: str | None = None
