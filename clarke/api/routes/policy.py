"""Policy management endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from clarke.api.deps import get_session
from clarke.api.schemas.policy import (
    ApprovePolicyRequest,
    CreatePolicyRequest,
    PolicyListItem,
    PolicyResponse,
)
from clarke.memory.policy import PolicyService
from clarke.storage.postgres.repositories.audit_repo import create_audit_event

router = APIRouter(prefix="/policy", tags=["policy"])


@router.post("", response_model=PolicyResponse)
async def create_policy(
    request: CreatePolicyRequest,
    session: AsyncSession = Depends(get_session),
) -> PolicyResponse:
    service = PolicyService()
    result = await service.create_policy(
        session,
        request.tenant_id,
        request.content,
        request.owner_id,
        auto_approve=request.auto_approve,
    )
    await create_audit_event(
        session,
        tenant_id=request.tenant_id,
        actor_id=request.owner_id,
        action="policy_created" if not request.auto_approve else "policy_auto_approved",
        target_type="policy",
        target_id=result["id"],
    )
    await session.commit()
    return PolicyResponse(**result)


@router.post("/{policy_id}/approve", response_model=PolicyResponse)
async def approve_policy(
    policy_id: str,
    request: ApprovePolicyRequest,
    session: AsyncSession = Depends(get_session),
) -> PolicyResponse:
    service = PolicyService()
    result = await service.approve_policy(session, policy_id, request.approver_id, request.comment)
    await create_audit_event(
        session,
        tenant_id="system",
        actor_id=request.approver_id,
        action="policy_approved",
        target_type="policy",
        target_id=policy_id,
        reason=request.comment,
    )
    await session.commit()
    return PolicyResponse(**result)


@router.post("/{policy_id}/reject", response_model=PolicyResponse)
async def reject_policy(
    policy_id: str,
    request: ApprovePolicyRequest,
    session: AsyncSession = Depends(get_session),
) -> PolicyResponse:
    service = PolicyService()
    result = await service.reject_policy(session, policy_id, request.approver_id, request.comment)
    await create_audit_event(
        session,
        tenant_id="system",
        actor_id=request.approver_id,
        action="policy_rejected",
        target_type="policy",
        target_id=policy_id,
        reason=request.comment,
    )
    await session.commit()
    return PolicyResponse(**result)


@router.post("/{policy_id}/submit", response_model=PolicyResponse)
async def submit_policy(
    policy_id: str,
    request: ApprovePolicyRequest,
    session: AsyncSession = Depends(get_session),
) -> PolicyResponse:
    service = PolicyService()
    result = await service.submit_for_approval(session, policy_id, request.approver_id)
    await session.commit()
    return PolicyResponse(**result)


@router.get("", response_model=list[PolicyListItem])
async def list_policies(
    tenant_id: str,
    status: str | None = None,
    session: AsyncSession = Depends(get_session),
) -> list[PolicyListItem]:
    service = PolicyService()
    if status and status != "active":
        policies = await service.get_by_status(session, tenant_id, status)
    else:
        policies = await service.get_active(session, tenant_id)
    return [PolicyListItem(**p) for p in policies]
