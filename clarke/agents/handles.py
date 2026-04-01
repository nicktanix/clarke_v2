"""Agent handle creation and management."""

from dataclasses import dataclass
from datetime import timedelta

from clarke.utils.time import utc_now


@dataclass
class AgentHandle:
    subagent_handle: str
    query_url: str
    expires_at: str


def build_handle(
    agent_id: str,
    timeout_minutes: int = 30,
) -> AgentHandle:
    """Build a scoped agent handle for the parent to use."""
    expires = utc_now() + timedelta(minutes=timeout_minutes)
    return AgentHandle(
        subagent_handle=agent_id,
        query_url=f"/query?agent_id={agent_id}",
        expires_at=expires.isoformat(),
    )
