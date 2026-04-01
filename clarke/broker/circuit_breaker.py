"""Circuit breaker pattern for external service calls.

Prevents cascading failures by temporarily disabling calls to unhealthy services.
States: CLOSED (normal) → OPEN (failing, skip calls) → HALF_OPEN (testing recovery).
"""

import time
from enum import StrEnum

from clarke.telemetry.logging import get_logger

logger = get_logger(__name__)


class CircuitState(StrEnum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """Circuit breaker with configurable thresholds and recovery timeout."""

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout_s: float = 30.0,
    ) -> None:
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout_s = recovery_timeout_s
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time = 0.0

    @property
    def state(self) -> CircuitState:
        if (
            self._state == CircuitState.OPEN
            and time.time() - self._last_failure_time >= self.recovery_timeout_s
        ):
            self._state = CircuitState.HALF_OPEN
            logger.info("circuit_half_open", name=self.name)
        return self._state

    @property
    def is_available(self) -> bool:
        """True if the circuit allows calls (CLOSED or HALF_OPEN)."""
        return self.state != CircuitState.OPEN

    def record_success(self) -> None:
        """Record a successful call. Closes the circuit if half-open."""
        if self._state == CircuitState.HALF_OPEN:
            self._state = CircuitState.CLOSED
            logger.info("circuit_closed", name=self.name)
        self._failure_count = 0

    def record_failure(self) -> None:
        """Record a failed call. Opens the circuit if threshold exceeded."""
        self._failure_count += 1
        self._last_failure_time = time.time()

        if self._failure_count >= self.failure_threshold:
            self._state = CircuitState.OPEN
            logger.warning(
                "circuit_opened",
                name=self.name,
                failures=self._failure_count,
                recovery_s=self.recovery_timeout_s,
            )

    def reset(self) -> None:
        """Reset the circuit to closed state."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time = 0.0


# Module-level circuit breaker instances
qdrant_circuit = CircuitBreaker("qdrant", failure_threshold=5, recovery_timeout_s=30.0)
neo4j_circuit = CircuitBreaker("neo4j", failure_threshold=5, recovery_timeout_s=30.0)
llm_circuit = CircuitBreaker("llm", failure_threshold=3, recovery_timeout_s=60.0)
