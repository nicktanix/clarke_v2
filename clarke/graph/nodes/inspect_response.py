"""Inspect model response for CONTEXT_REQUEST or SUBAGENT_SPAWN structures."""

import json

from clarke.graph.state import BrokerState
from clarke.telemetry.logging import get_logger

logger = get_logger(__name__)


def inspect_response(state: BrokerState) -> dict:
    response = state.get("model_response") or ""
    context_request_detected = False
    subagent_spawn_requested = False
    context_request = None
    spawn_request = None

    try:
        # Strategy 1: Try to find JSON blocks in the response (single-line or multi-line)
        # Extract JSON from markdown code blocks first
        import re

        json_blocks = re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", response, re.DOTALL)

        # Strategy 2: Also try line-by-line for bare JSON
        for line in response.split("\n"):
            line = line.strip()
            if line.startswith("{") and line.endswith("}"):
                json_blocks.append(line)

        for block in json_blocks:
            try:
                parsed = json.loads(block)
                if parsed.get("type") == "CONTEXT_REQUEST":
                    context_request_detected = True
                    context_request = parsed
                    logger.info(
                        "context_request_detected", requests=len(parsed.get("requests", []))
                    )
                elif parsed.get("type") == "SUBAGENT_SPAWN":
                    subagent_spawn_requested = True
                    spawn_request = parsed
                    logger.info("subagent_spawn_detected", task=parsed.get("task", "")[:50])
            except json.JSONDecodeError:
                continue
    except Exception:
        pass

    return {
        "context_request_detected": context_request_detected,
        "context_request": context_request,
        "subagent_spawn_requested": subagent_spawn_requested,
        "subagent_spawn_approved": False,
        "spawn_request": spawn_request,
    }
