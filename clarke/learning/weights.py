"""Source weight management and online learning."""

from sqlalchemy.ext.asyncio import AsyncSession

from clarke.settings import LearningSettings
from clarke.storage.postgres.repositories.weight_repo import (
    get_or_create_weight,
)
from clarke.storage.postgres.repositories.weight_repo import (
    update_weight as update_weight_db,
)
from clarke.telemetry.logging import get_logger

logger = get_logger(__name__)


def compute_weight_update(
    old_weight: float,
    usefulness_score: float,
    learning_rate: float = 0.05,
) -> float:
    """Apply online update rule: new = old * (1 - lr) + usefulness * lr."""
    return old_weight * (1 - learning_rate) + usefulness_score * learning_rate


def decay_epsilon(
    current_epsilon: float,
    decay_rate: float = 0.995,
    min_epsilon: float = 0.05,
) -> float:
    """Decay exploration rate, respecting floor."""
    return max(current_epsilon * decay_rate, min_epsilon)


async def apply_weight_updates(
    session: AsyncSession,
    tenant_id: str,
    source_usefulness: dict[str, float],
    settings: LearningSettings,
) -> None:
    """Load current weights, apply update rule, persist.

    source_usefulness maps "source:strategy" keys to usefulness scores.
    """
    for key, usefulness in source_usefulness.items():
        parts = key.split(":", 1)
        source = parts[0]
        strategy = parts[1] if len(parts) > 1 else "direct"

        weight_record = await get_or_create_weight(
            session,
            tenant_id=tenant_id,
            source=source,
            strategy=strategy,
            default_weight=0.5,
            default_epsilon=settings.epsilon_initial,
        )

        new_weight = compute_weight_update(
            weight_record.weight,
            usefulness,
            settings.weight_learning_rate,
        )
        new_epsilon = decay_epsilon(
            weight_record.epsilon,
            settings.epsilon_decay_rate,
            settings.epsilon_min,
        )

        await update_weight_db(session, weight_record.id, new_weight, new_epsilon)

    logger.info(
        "weights_updated",
        tenant_id=tenant_id,
        sources_updated=len(source_usefulness),
    )
