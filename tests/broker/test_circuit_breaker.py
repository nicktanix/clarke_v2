"""Circuit breaker tests."""

import time

from clarke.broker.circuit_breaker import CircuitBreaker, CircuitState


def test_circuit_starts_closed():
    cb = CircuitBreaker("test")
    assert cb.state == CircuitState.CLOSED
    assert cb.is_available is True


def test_circuit_opens_after_threshold():
    cb = CircuitBreaker("test", failure_threshold=3)
    cb.record_failure()
    cb.record_failure()
    assert cb.state == CircuitState.CLOSED
    cb.record_failure()
    assert cb.state == CircuitState.OPEN
    assert cb.is_available is False


def test_circuit_half_opens_after_timeout():
    cb = CircuitBreaker("test", failure_threshold=2, recovery_timeout_s=0.1)
    cb.record_failure()
    cb.record_failure()
    assert cb.state == CircuitState.OPEN

    time.sleep(0.15)
    assert cb.state == CircuitState.HALF_OPEN
    assert cb.is_available is True


def test_circuit_closes_on_success_from_half_open():
    cb = CircuitBreaker("test", failure_threshold=2, recovery_timeout_s=0.1)
    cb.record_failure()
    cb.record_failure()
    time.sleep(0.15)
    assert cb.state == CircuitState.HALF_OPEN

    cb.record_success()
    assert cb.state == CircuitState.CLOSED


def test_circuit_reopens_on_failure_from_half_open():
    cb = CircuitBreaker("test", failure_threshold=1, recovery_timeout_s=0.1)
    cb.record_failure()
    time.sleep(0.15)
    assert cb.state == CircuitState.HALF_OPEN

    cb.record_failure()
    assert cb.state == CircuitState.OPEN


def test_circuit_reset():
    cb = CircuitBreaker("test", failure_threshold=2)
    cb.record_failure()
    cb.record_failure()
    assert cb.state == CircuitState.OPEN
    cb.reset()
    assert cb.state == CircuitState.CLOSED
    assert cb.is_available is True
