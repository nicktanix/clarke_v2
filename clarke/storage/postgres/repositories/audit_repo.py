"""Repository for audit_events table."""

from sqlalchemy.ext.asyncio import AsyncSession

from clarke.storage.postgres.models import AuditEvent


async def create_audit_event(
    session: AsyncSession,
    tenant_id: str,
    actor_id: str,
    action: str,
    target_type: str,
    target_id: str,
    reason: str | None = None,
    metadata: dict | None = None,
) -> None:
    """Append an immutable audit event."""
    event = AuditEvent(
        tenant_id=tenant_id,
        actor_id=actor_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        reason=reason,
        metadata_=metadata,
    )
    session.add(event)
    await session.flush()
