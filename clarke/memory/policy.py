"""Policy service — approval workflow and active policy retrieval."""

from sqlalchemy.ext.asyncio import AsyncSession

from clarke.storage.postgres.repositories.policy_repo import (
    create_policy_approval,
    create_policy_node,
    get_active_policies,
    get_policies_by_status,
    update_policy_status,
)


class PolicyService:
    async def create_policy(
        self,
        session: AsyncSession,
        tenant_id: str,
        content: str,
        owner_id: str,
        auto_approve: bool = False,
    ) -> dict:
        record = await create_policy_node(
            session,
            {
                "tenant_id": tenant_id,
                "content": content,
                "status": "active" if auto_approve else "draft",
                "owner_id": owner_id,
            },
        )
        return {"id": record.id, "status": record.status}

    async def submit_for_approval(
        self, session: AsyncSession, policy_id: str, approver_id: str
    ) -> dict:
        await update_policy_status(session, policy_id, "pending_approval", approver_id=approver_id)
        await create_policy_approval(
            session,
            {
                "policy_node_id": policy_id,
                "approver_id": approver_id,
                "status": "pending",
            },
        )
        return {"id": policy_id, "status": "pending_approval"}

    async def approve_policy(
        self, session: AsyncSession, policy_id: str, approver_id: str, comment: str | None = None
    ) -> dict:
        await update_policy_status(session, policy_id, "active")
        await create_policy_approval(
            session,
            {
                "policy_node_id": policy_id,
                "approver_id": approver_id,
                "status": "approved",
                "comment": comment,
            },
        )
        return {"id": policy_id, "status": "active"}

    async def reject_policy(
        self, session: AsyncSession, policy_id: str, approver_id: str, comment: str | None = None
    ) -> dict:
        await update_policy_status(session, policy_id, "draft")
        await create_policy_approval(
            session,
            {
                "policy_node_id": policy_id,
                "approver_id": approver_id,
                "status": "rejected",
                "comment": comment,
            },
        )
        return {"id": policy_id, "status": "draft"}

    async def get_active(self, session: AsyncSession, tenant_id: str) -> list[dict]:
        policies = await get_active_policies(session, tenant_id)
        return [
            {"id": p.id, "content": p.content, "source": "policy", "status": p.status}
            for p in policies
        ]

    async def get_by_status(self, session: AsyncSession, tenant_id: str, status: str) -> list[dict]:
        policies = await get_policies_by_status(session, tenant_id, status)
        return [
            {"id": p.id, "content": p.content, "source": "policy", "status": p.status}
            for p in policies
        ]
