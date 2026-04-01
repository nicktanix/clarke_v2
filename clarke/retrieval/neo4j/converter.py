"""Convert Neo4j traversal results to RetrievedItem objects."""

from clarke.api.schemas.retrieval import Provenance, RetrievedItem


def graph_results_to_retrieved_items(
    results: list[dict],
    tenant_id: str,
    project_id: str,
    source: str = "graph",
) -> list[RetrievedItem]:
    """Convert Neo4j traversal results to normalized RetrievedItem objects."""
    items: list[RetrievedItem] = []

    for record in results:
        name = record.get("name", "")
        content = record.get("content") or name
        node_type = record.get("node_type", "entity")
        confidence = record.get("confidence", 0.5)

        items.append(
            RetrievedItem(
                item_id=str(record.get("id", name)),
                tenant_id=tenant_id,
                project_id=project_id,
                source=source,
                node_type=node_type.lower() if node_type else "entity",
                score=min(float(confidence), 1.0),
                summary=content[:500] if content else name,
                provenance=Provenance(),
            )
        )

    return items
