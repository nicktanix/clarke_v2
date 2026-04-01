"""Check health of retrieval dependencies and set execution mode."""

from clarke.broker.degraded_mode import check_dependency_health
from clarke.graph.state import BrokerState


async def check_health(state: BrokerState) -> dict:
    """Check dependency health and set execution mode."""
    mode, health_status = await check_dependency_health()
    return {
        "degraded_mode": mode != "full",
        "execution_mode": str(mode),
        "health_status": health_status,
    }
