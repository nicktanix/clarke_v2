"""Validate a CONTEXT_REQUEST before second-pass retrieval."""

from clarke.graph.state import BrokerState
from clarke.settings import get_settings
from clarke.telemetry.logging import get_logger

logger = get_logger(__name__)


def validate_context_request(state: BrokerState) -> dict:
    """Validate the context request against broker policy.

    Checks: loop count, allowed sources, max items, non-empty why.
    If validation fails, clears context_request_detected to skip second pass.
    """
    settings = get_settings()
    cr = state.get("context_request")
    loop_count = state.get("retrieval_loop_count", 0)

    if not cr or not cr.get("requests"):
        logger.info("context_request_empty")
        return {"context_request_detected": False, "context_request": None}

    if loop_count >= settings.broker.max_retrieval_loops:
        logger.info("context_request_at_max_loops", loop_count=loop_count)
        return {"context_request_detected": False, "context_request": None}

    allowed_sources = set(settings.learning.allowed_context_request_sources)
    max_items = settings.learning.max_context_request_items
    total_requested = 0

    for req in cr["requests"]:
        source = req.get("source", "")
        if source not in allowed_sources:
            logger.info("context_request_rejected_bad_source", source=source)
            return {"context_request_detected": False, "context_request": None}

        why = req.get("why", "").strip()
        if not why:
            logger.info("context_request_rejected_empty_why")
            return {"context_request_detected": False, "context_request": None}

        req_items = req.get("max_items", 3)
        total_requested += req_items

    if total_requested > max_items:
        logger.info(
            "context_request_rejected_too_many_items",
            total=total_requested,
            max=max_items,
        )
        return {"context_request_detected": False, "context_request": None}

    logger.info("context_request_validated", requests=len(cr["requests"]))
    return {"retrieval_loop_count": loop_count + 1}
