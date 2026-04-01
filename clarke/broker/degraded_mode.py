"""Degraded mode definitions and health checking with circuit breakers."""

from enum import StrEnum

from clarke.broker.circuit_breaker import neo4j_circuit, qdrant_circuit
from clarke.telemetry.logging import get_logger

logger = get_logger(__name__)


class DegradedMode(StrEnum):
    FULL = "full"
    REDUCED = "reduced"
    CANONICAL_ONLY = "canonical_only"


async def check_dependency_health() -> tuple[DegradedMode, dict]:
    """Check health of all retrieval dependencies with circuit breaker awareness.

    If a circuit is OPEN, skip the health check (known unhealthy).
    If CLOSED or HALF_OPEN, perform the check and update the circuit.
    """
    qdrant_ok = False
    if qdrant_circuit.is_available:
        try:
            from clarke.retrieval.qdrant.client import get_qdrant_store

            store = get_qdrant_store()
            qdrant_ok = await store.health_check()
            if qdrant_ok:
                qdrant_circuit.record_success()
            else:
                qdrant_circuit.record_failure()
        except RuntimeError:
            pass
        except Exception:
            qdrant_circuit.record_failure()
            logger.warning("qdrant_health_check_failed", exc_info=True)

    neo4j_ok = False
    if neo4j_circuit.is_available:
        try:
            from clarke.retrieval.neo4j.client import get_neo4j_store

            store = get_neo4j_store()
            neo4j_ok = await store.health_check()
            if neo4j_ok:
                neo4j_circuit.record_success()
            else:
                neo4j_circuit.record_failure()
        except RuntimeError:
            pass
        except Exception:
            neo4j_circuit.record_failure()
            logger.warning("neo4j_health_check_failed", exc_info=True)

    health_status = {
        "postgres": True,
        "qdrant": qdrant_ok,
        "qdrant_circuit": qdrant_circuit.state,
        "neo4j": neo4j_ok,
        "neo4j_circuit": neo4j_circuit.state,
    }

    if not qdrant_ok and not neo4j_ok:
        return DegradedMode.CANONICAL_ONLY, health_status
    if not qdrant_ok:
        return DegradedMode.REDUCED, health_status
    return DegradedMode.FULL, health_status
