"""Error hierarchy for CLARKE."""


class ClarkeError(Exception):
    """Base error for all CLARKE errors."""

    def __init__(self, message: str, *, request_id: str | None = None) -> None:
        super().__init__(message)
        self.request_id = request_id


class RequestValidationError(ClarkeError):
    """Invalid request data."""


class BrokerError(ClarkeError):
    """Broker-level processing error."""


class DegradedModeError(ClarkeError):
    """Signals that the system is operating in degraded mode."""


class BudgetExceededError(ClarkeError):
    """Token or cost budget exceeded."""
