"""Directive service — approval workflow for proposed behavioral directives."""

from sqlalchemy.ext.asyncio import AsyncSession

from clarke.storage.postgres.repositories.agent_profile_repo import (
    get_agent_profile,
    update_agent_profile,
)
from clarke.storage.postgres.repositories.audit_repo import create_audit_event
from clarke.storage.postgres.repositories.directive_proposal_repo import (
    get_proposal,
    list_proposals,
    update_proposal_status,
)
from clarke.telemetry.logging import get_logger

logger = get_logger(__name__)


class DirectiveService:
    async def get_proposals(
        self,
        session: AsyncSession,
        agent_profile_id: str,
        status: str | None = None,
    ) -> list[dict]:
        proposals = await list_proposals(session, agent_profile_id, status)
        return [
            {
                "id": p.id,
                "proposed_directive": p.proposed_directive,
                "source_memory_ids": p.source_memory_ids,
                "cluster_size": p.cluster_size,
                "similarity_score": p.similarity_score,
                "status": p.status,
                "proposed_at": p.proposed_at.isoformat() if p.proposed_at else None,
                "reviewed_by": p.reviewed_by,
                "review_comment": p.review_comment,
            }
            for p in proposals
        ]

    async def approve_proposal(
        self,
        session: AsyncSession,
        proposal_id: str,
        approver_id: str,
        comment: str | None = None,
    ) -> dict:
        """Approve a directive proposal and apply it to the agent profile."""
        proposal = await get_proposal(session, proposal_id)
        if not proposal:
            raise ValueError("Proposal not found")
        if proposal.status not in ("pending_approval", "draft"):
            raise ValueError(f"Proposal is {proposal.status}, cannot approve")

        # Load agent profile
        profile = await get_agent_profile(session, proposal.agent_profile_id)
        if not profile:
            raise ValueError("Agent profile not found")

        # Append directive to behavioral_directives
        directives = list(profile.behavioral_directives or [])
        directives.append(proposal.proposed_directive)
        new_version = profile.version + 1

        await update_agent_profile(
            session,
            profile.id,
            {"behavioral_directives": directives, "version": new_version},
        )

        # Update proposal status
        await update_proposal_status(
            session,
            proposal_id,
            status="applied",
            reviewed_by=approver_id,
            review_comment=comment,
            applied_version=new_version,
        )

        # Audit
        await create_audit_event(
            session,
            tenant_id=proposal.tenant_id,
            actor_id=approver_id,
            action="directive_applied",
            target_type="agent_profile",
            target_id=proposal.agent_profile_id,
            metadata={
                "proposal_id": proposal_id,
                "directive": proposal.proposed_directive,
                "new_version": new_version,
            },
        )

        logger.info(
            "directive_approved_and_applied",
            proposal_id=proposal_id,
            agent_profile_id=proposal.agent_profile_id,
            new_version=new_version,
        )

        return {"status": "applied", "version": new_version}

    async def reject_proposal(
        self,
        session: AsyncSession,
        proposal_id: str,
        approver_id: str,
        comment: str | None = None,
    ) -> dict:
        """Reject a directive proposal."""
        proposal = await get_proposal(session, proposal_id)
        if not proposal:
            raise ValueError("Proposal not found")

        await update_proposal_status(
            session,
            proposal_id,
            status="rejected",
            reviewed_by=approver_id,
            review_comment=comment,
        )

        await create_audit_event(
            session,
            tenant_id=proposal.tenant_id,
            actor_id=approver_id,
            action="directive_rejected",
            target_type="agent_profile",
            target_id=proposal.agent_profile_id,
            metadata={"proposal_id": proposal_id, "reason": comment},
        )

        return {"status": "rejected"}
