"""Build graph nodes in Neo4j from ingested document chunks."""

import re

from clarke.telemetry.logging import get_logger

logger = get_logger(__name__)

_ENTITY_PATTERN = re.compile(r"\b([A-Z]\w+(?:\s+[A-Z]\w+)+)\b")


def extract_entities(text: str) -> list[str]:
    """Extract candidate entities from text (capitalized multi-word sequences)."""
    matches = _ENTITY_PATTERN.findall(text)
    seen: set[str] = set()
    entities: list[str] = []
    for m in matches:
        normalized = m.strip()
        if normalized.lower() not in seen and len(normalized) > 3:
            seen.add(normalized.lower())
            entities.append(normalized)
    return entities


async def build_graph_nodes(
    tenant_id: str,
    project_id: str,
    document_id: str,
    chunks: list,
) -> None:
    """Extract entities/concepts from chunks and create Neo4j nodes + edges.

    Uses MERGE to avoid duplicates. Best-effort — failures don't block ingestion.
    """
    from clarke.retrieval.neo4j.client import get_neo4j_store

    store = get_neo4j_store()

    # Create Document node
    await store.execute_write(
        """
        MERGE (d:Document {id: $doc_id, tenant_id: $tenant_id, project_id: $project_id})
        """,
        {"doc_id": document_id, "tenant_id": tenant_id, "project_id": project_id},
    )

    for chunk in chunks:
        chunk_id = chunk.metadata.get("chunk_db_id", str(chunk.chunk_index))
        heading = chunk.metadata.get("heading")

        # Create Chunk node and link to Document
        await store.execute_write(
            """
            MERGE (c:Chunk {id: $chunk_id, tenant_id: $tenant_id, project_id: $project_id})
            SET c.content = $content
            WITH c
            MATCH (d:Document {id: $doc_id, tenant_id: $tenant_id})
            MERGE (d)-[:CONTAINS]->(c)
            """,
            {
                "chunk_id": chunk_id,
                "tenant_id": tenant_id,
                "project_id": project_id,
                "content": chunk.content[:500],
                "doc_id": document_id,
            },
        )

        # Create Concept from heading if available
        if heading:
            await store.execute_write(
                """
                MERGE (concept:Concept {name: $name, tenant_id: $tenant_id, project_id: $project_id})
                WITH concept
                MATCH (c:Chunk {id: $chunk_id, tenant_id: $tenant_id})
                MERGE (c)-[r:ABOUT]->(concept)
                SET r.tenant_id = $tenant_id, r.confidence = 1.0
                """,
                {
                    "name": heading,
                    "tenant_id": tenant_id,
                    "project_id": project_id,
                    "chunk_id": chunk_id,
                },
            )

        # Extract entities and create Entity nodes
        entities = extract_entities(chunk.content)
        for entity_name in entities[:10]:  # limit per chunk
            await store.execute_write(
                """
                MERGE (e:Entity {name: $name, tenant_id: $tenant_id, project_id: $project_id})
                WITH e
                MATCH (c:Chunk {id: $chunk_id, tenant_id: $tenant_id})
                MERGE (c)-[r:MENTIONS]->(e)
                SET r.tenant_id = $tenant_id, r.confidence = 1.0
                """,
                {
                    "name": entity_name,
                    "tenant_id": tenant_id,
                    "project_id": project_id,
                    "chunk_id": chunk_id,
                },
            )

    logger.info(
        "graph_build_completed",
        document_id=document_id,
        chunk_count=len(chunks),
    )
