"""Context request schemas (Phase 3 — stubbed)."""

from typing import Literal

from pydantic import BaseModel


class ContextRequestItem(BaseModel):
    source: str
    query: str
    why: str
    max_items: int = 3


class ContextRequest(BaseModel):
    type: Literal["CONTEXT_REQUEST"] = "CONTEXT_REQUEST"
    requests: list[ContextRequestItem] = []
