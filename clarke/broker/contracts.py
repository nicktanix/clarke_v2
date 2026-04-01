"""Broker internal contracts."""

from pydantic import BaseModel

from clarke.api.schemas.retrieval import ContextPack


class BrokerContract(BaseModel):
    """What the broker promises for a single request."""

    request_id: str
    tenant_id: str
    project_id: str
    user_id: str
    context_pack: ContextPack = ContextPack()
    model_response: str | None = None
    degraded_mode: bool = False
    episode_id: str | None = None
