"""Qdrant filter builders for tenant isolation."""

from qdrant_client.models import FieldCondition, Filter, MatchValue


def tenant_project_filter(tenant_id: str, project_id: str) -> Filter:
    """Mandatory filter for tenant isolation."""
    return Filter(
        must=[
            FieldCondition(key="tenant_id", match=MatchValue(value=tenant_id)),
            FieldCondition(key="project_id", match=MatchValue(value=project_id)),
        ]
    )


def build_search_filter(
    tenant_id: str,
    project_id: str,
    source_type: str | None = None,
) -> Filter:
    """Build composite filter with optional source_type constraint."""
    conditions = [
        FieldCondition(key="tenant_id", match=MatchValue(value=tenant_id)),
        FieldCondition(key="project_id", match=MatchValue(value=project_id)),
    ]
    if source_type:
        conditions.append(FieldCondition(key="source_type", match=MatchValue(value=source_type)))
    return Filter(must=conditions)
