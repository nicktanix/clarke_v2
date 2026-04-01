"""Retrieval-related schemas."""

from pydantic import BaseModel


class RetrievalConstraints(BaseModel):
    max_items: int = 5
    prefer_recent: bool = False
    trust_min: float = 0.0
    timeout_ms: int = 800


class RetrievalRequest(BaseModel):
    source: str  # docs | memory | decisions | graph | recent_history | policy
    strategy: str  # direct | leaf_first | convergence_anchor | decision_lineage | hybrid
    query: str
    weight: float = 0.0
    constraints: RetrievalConstraints = RetrievalConstraints()


class Provenance(BaseModel):
    doc_id: str | None = None
    section: str | None = None
    page: int | None = None


class RetrievedItem(BaseModel):
    item_id: str
    tenant_id: str
    project_id: str
    source: str
    node_type: str
    score: float
    summary: str
    provenance: Provenance = Provenance()


class ContextBudget(BaseModel):
    input_tokens: int = 0
    actual_tokenizer: str = "estimated"


class ContextPack(BaseModel):
    policy: list[str] = []
    anchors: list[dict] = []
    evidence: list[dict] = []
    recent_state: list[dict] = []
    budget: ContextBudget = ContextBudget()
