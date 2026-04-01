"""Validate incoming request and ensure required fields are present."""

from clarke.graph.state import BrokerState
from clarke.utils.ids import generate_request_id


def validate_request(state: BrokerState) -> dict:
    if not state.get("request_id"):
        state["request_id"] = generate_request_id()

    errors = []
    for field in ("tenant_id", "project_id", "user_id", "message"):
        if not state.get(field):
            errors.append(f"Missing required field: {field}")

    if errors:
        return {"error": "; ".join(errors)}

    return {
        "request_id": state["request_id"],
        "agent_depth": state.get("agent_depth", 0),
    }
