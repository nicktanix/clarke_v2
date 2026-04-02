"""Policy management schemas."""

from pydantic import BaseModel


class CreatePolicyRequest(BaseModel):
    tenant_id: str
    content: str
    owner_id: str
    auto_approve: bool = False


class ApprovePolicyRequest(BaseModel):
    approver_id: str
    comment: str | None = None


class PolicyResponse(BaseModel):
    id: str
    status: str


class PolicyListItem(BaseModel):
    id: str
    content: str
    status: str
    source: str = "policy"
