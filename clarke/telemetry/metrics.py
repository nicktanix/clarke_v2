"""OpenTelemetry metric instruments for CLARKE observability (spec §7.11)."""

from opentelemetry import metrics

from clarke.telemetry.logging import get_logger

logger = get_logger(__name__)

# Get or create the meter
_meter = metrics.get_meter("clarke")

# Histograms
request_latency_histogram = _meter.create_histogram(
    name="clarke.request.latency_ms",
    description="End-to-end request latency in milliseconds",
    unit="ms",
)

retrieval_latency_histogram = _meter.create_histogram(
    name="clarke.retrieval.latency_ms",
    description="Retrieval pipeline latency in milliseconds",
    unit="ms",
)

# Counters
request_counter = _meter.create_counter(
    name="clarke.requests.total",
    description="Total number of query requests",
)

degraded_mode_counter = _meter.create_counter(
    name="clarke.degraded_mode.count",
    description="Number of requests served in degraded mode",
)

loop_invocation_counter = _meter.create_counter(
    name="clarke.loop.invocation_count",
    description="Number of CONTEXT_REQUEST second-pass invocations",
)

spawn_requested_counter = _meter.create_counter(
    name="clarke.spawn.requested",
    description="Number of SUBAGENT_SPAWN requests",
)

spawn_approved_counter = _meter.create_counter(
    name="clarke.spawn.approved",
    description="Number of approved sub-agent spawns",
)

# Gauges (via UpDownCounter for UCR tracking)
ucr_histogram = _meter.create_histogram(
    name="clarke.context.useful_ratio",
    description="Useful Context Ratio per request",
)


def record_request_latency(latency_ms: int, *, tenant_id: str) -> None:
    """Record request latency."""
    request_latency_histogram.record(latency_ms, {"tenant_id": tenant_id})
    request_counter.add(1, {"tenant_id": tenant_id})


def record_degraded_mode(*, tenant_id: str, mode: str) -> None:
    """Record a degraded mode activation."""
    degraded_mode_counter.add(1, {"tenant_id": tenant_id, "mode": mode})


def record_loop_invocation(*, tenant_id: str) -> None:
    """Record a CONTEXT_REQUEST second-pass invocation."""
    loop_invocation_counter.add(1, {"tenant_id": tenant_id})


def record_spawn(*, tenant_id: str, approved: bool) -> None:
    """Record a sub-agent spawn request."""
    spawn_requested_counter.add(1, {"tenant_id": tenant_id})
    if approved:
        spawn_approved_counter.add(1, {"tenant_id": tenant_id})


def record_ucr(ucr: float, *, tenant_id: str) -> None:
    """Record useful context ratio."""
    ucr_histogram.record(ucr, {"tenant_id": tenant_id})
