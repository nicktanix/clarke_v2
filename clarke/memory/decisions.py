"""Decision service — record and query structured decisions."""

from sqlalchemy.ext.asyncio import AsyncSession

from clarke.storage.postgres.repositories.decision_repo import (
    create_decision,
    get_decisions_by_keywords,
    update_decision_status,
)
from clarke.utils.time import utc_now


class DecisionService:
    async def record_decision(
        self,
        session: AsyncSession,
        tenant_id: str,
        project_id: str,
        title: str,
        rationale: str,
        decided_by: str,
        alternatives: list[dict] | None = None,
    ) -> dict:
        record = await create_decision(
            session,
            {
                "tenant_id": tenant_id,
                "project_id": project_id,
                "title": title,
                "rationale": rationale,
                "decided_by": decided_by,
                "decided_at": utc_now(),
                "alternatives": alternatives,
            },
        )
        return {"id": record.id, "title": record.title, "status": record.status}

    async def get_relevant_decisions(
        self,
        session: AsyncSession,
        tenant_id: str,
        project_id: str,
        keywords: list[str],
        limit: int = 5,
    ) -> list[dict]:
        decisions = await get_decisions_by_keywords(session, tenant_id, project_id, keywords, limit)
        return [
            {
                "id": d.id,
                "title": d.title,
                "rationale": d.rationale,
                "source": "decisions",
                "status": d.status,
                "decided_at": d.decided_at.isoformat(),
            }
            for d in decisions
        ]

    async def supersede_decision(self, session: AsyncSession, decision_id: str) -> dict:
        await update_decision_status(session, decision_id, "superseded")
        return {"id": decision_id, "status": "superseded"}
