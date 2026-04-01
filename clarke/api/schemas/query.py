"""Query request/response schemas."""

from pydantic import BaseModel, Field

from clarke.utils.ids import generate_request_id


class BrokerQueryRequest(BaseModel):
    request_id: str = Field(default_factory=generate_request_id)
    tenant_id: str
    project_id: str
    session_id: str | None = None
    user_id: str
    message: str
    stream: bool = False
    agent_id: str | None = None


class BrokerQueryResponse(BaseModel):
    request_id: str
    answer: str
    degraded_mode: bool = False
    trace_id: str | None = None
    prompt_version_id: str | None = None
    context_template_version_id: str | None = None
    subagent_handle: str | None = None
    subagent_query_url: str | None = None
