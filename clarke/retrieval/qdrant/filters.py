"""Qdrant filter builders for tenant isolation."""

from qdrant_client.models import FieldCondition, Filter, MatchAny, MatchValue


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


def build_skill_search_filter(
    tenant_id: str,
    project_id: str,
    capabilities: list[str] | None = None,
) -> Filter:
    """Build filter for skill document retrieval with optional capability matching."""
    conditions = [
        FieldCondition(key="tenant_id", match=MatchValue(value=tenant_id)),
        FieldCondition(key="project_id", match=MatchValue(value=project_id)),
        FieldCondition(key="source_type", match=MatchValue(value="skill")),
    ]
    if capabilities:
        conditions.append(
            FieldCondition(key="agent_capabilities", match=MatchAny(any=capabilities))
        )
    return Filter(must=conditions)
