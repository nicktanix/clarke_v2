"""Common API schemas."""

from pydantic import BaseModel


class TenantScope(BaseModel):
    tenant_id: str
    project_id: str
    user_id: str


class ErrorResponse(BaseModel):
    error: str
    detail: str | None = None
    request_id: str | None = None


class HealthCheck(BaseModel):
    name: str
    status: str


class HealthResponse(BaseModel):
    status: str
    version: str
    checks: list[HealthCheck] = []
