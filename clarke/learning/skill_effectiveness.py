"""Skill effectiveness learning — EMA updates from feedback signals."""

from sqlalchemy.ext.asyncio import AsyncSession

from clarke.learning.weights import compute_weight_update, decay_epsilon
from clarke.settings import SelfImprovementSettings
from clarke.storage.postgres.repositories.skill_effectiveness_repo import (
    get_or_create,
    update_effectiveness,
)
from clarke.telemetry.logging import get_logger

logger = get_logger(__name__)


async def apply_skill_effectiveness_updates(
    session: AsyncSession,
    agent_profile_id: str,
    tenant_id: str,
    skills: list[str],
    usefulness: float,
    settings: SelfImprovementSettings,
) -> None:
    """Update effectiveness scores for all skills active in a session.

    Uses the same EMA formula as source weight updates:
    new = old * (1 - lr) + usefulness * lr
    """
    for skill_name in skills:
        record = await get_or_create(
            session,
            agent_profile_id=agent_profile_id,
            tenant_id=tenant_id,
            skill_name=skill_name,
            default_effectiveness=0.5,
            default_epsilon=settings.skill_effectiveness_epsilon_initial,
        )

        new_effectiveness = compute_weight_update(
            record.effectiveness,
            usefulness,
            settings.skill_effectiveness_learning_rate,
        )
        new_epsilon = decay_epsilon(
            record.epsilon,
            settings.skill_effectiveness_epsilon_decay,
            settings.skill_effectiveness_epsilon_min,
        )

        await update_effectiveness(session, record.id, new_effectiveness, new_epsilon)

    logger.info(
        "skill_effectiveness_updated",
        agent_profile_id=agent_profile_id,
        skills_updated=len(skills),
    )
