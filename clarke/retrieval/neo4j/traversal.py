"""Cypher traversal queries for graph-aware retrieval."""

from clarke.retrieval.neo4j.client import Neo4jStore
from clarke.telemetry.logging import get_logger

logger = get_logger(__name__)


class GraphTraversal:
    def __init__(self, store: Neo4jStore) -> None:
        self._store = store

    async def _update_last_retrieved(self, tenant_id: str, node_ids: list[str]) -> None:
        """Update last_retrieved_at on edges connected to retrieved nodes."""
        if not node_ids:
            return
        try:
            await self._store.execute_write(
                """
                MATCH (n)-[r]-()
                WHERE n.id IN $ids AND n.tenant_id = $tenant_id
                SET r.last_retrieved_at = datetime()
                """,
                {"ids": node_ids, "tenant_id": tenant_id},
            )
        except Exception:
            logger.debug("last_retrieved_at_update_failed", exc_info=True)

    async def find_related_entities(
        self,
        tenant_id: str,
        project_id: str,
        entity_names: list[str],
        max_hops: int = 2,
        limit: int = 10,
    ) -> list[dict]:
        """1-2 hop traversal from named entities to related concepts/chunks."""
        if not entity_names:
            return []

        hops = min(max_hops, 3)
        query = f"""
        MATCH (e {{tenant_id: $tenant_id, project_id: $project_id}})
        WHERE e.name IN $names AND (e:Entity OR e:Concept)
        MATCH path = (e)-[*1..{hops}]-(related)
        WHERE related.tenant_id = $tenant_id
        WITH related, min(length(path)) AS dist
        RETURN DISTINCT related.name AS name,
               labels(related)[0] AS node_type,
               related.content AS content,
               related.id AS id,
               1.0 / (1.0 + dist) AS confidence
        ORDER BY confidence DESC
        LIMIT $limit
        """

        results = await self._store.execute_read(
            query,
            {
                "tenant_id": tenant_id,
                "project_id": project_id,
                "names": entity_names,
                "limit": limit,
            },
        )
        await self._update_last_retrieved(
            tenant_id, [r.get("id", "") for r in results if r.get("id")]
        )
        return results

    async def find_concept_neighbors(
        self,
        tenant_id: str,
        project_id: str,
        concept_names: list[str],
        limit: int = 10,
    ) -> list[dict]:
        """Find concepts related to given concepts (convergence anchors)."""
        if not concept_names:
            return []

        query = """
        MATCH (c:Concept {tenant_id: $tenant_id, project_id: $project_id})
        WHERE c.name IN $names
        MATCH (c)-[r]-(neighbor)
        WHERE neighbor.tenant_id = $tenant_id
        RETURN DISTINCT neighbor.name AS name,
               labels(neighbor)[0] AS node_type,
               neighbor.content AS content,
               neighbor.id AS id,
               COALESCE(r.confidence, 0.5) AS confidence
        ORDER BY confidence DESC
        LIMIT $limit
        """

        results = await self._store.execute_read(
            query,
            {
                "tenant_id": tenant_id,
                "project_id": project_id,
                "names": concept_names,
                "limit": limit,
            },
        )
        await self._update_last_retrieved(
            tenant_id, [r.get("id", "") for r in results if r.get("id")]
        )
        return results

    async def find_convergence_anchors(
        self,
        tenant_id: str,
        project_id: str,
        chunk_ids: list[str],
        limit: int = 5,
    ) -> list[dict]:
        """Find shared graph parents of multiple semantic results (convergence)."""
        if len(chunk_ids) < 2:
            return []

        query = """
        MATCH (c1:Chunk {tenant_id: $tenant_id})-[:ABOUT|MENTIONS]->(concept)
        WHERE c1.id IN $chunk_ids AND concept.tenant_id = $tenant_id
        WITH concept, COUNT(DISTINCT c1) AS shared_count
        WHERE shared_count >= 2
        RETURN concept.name AS name,
               labels(concept)[0] AS node_type,
               concept.content AS content,
               concept.id AS id,
               shared_count,
               toFloat(shared_count) / $total AS confidence
        ORDER BY shared_count DESC
        LIMIT $limit
        """

        return await self._store.execute_read(
            query,
            {
                "tenant_id": tenant_id,
                "chunk_ids": chunk_ids,
                "total": len(chunk_ids),
                "limit": limit,
            },
        )

    async def find_decision_lineage(
        self,
        tenant_id: str,
        project_id: str,
        topic_keywords: list[str],
        limit: int = 5,
    ) -> list[dict]:
        """Find decisions related to topic via graph edges."""
        if not topic_keywords:
            return []

        # Build a WHERE clause that checks if any keyword appears in the concept name
        query = """
        MATCH (d:Decision {tenant_id: $tenant_id, project_id: $project_id})-[:ABOUT]->(c:Concept)
        WHERE ANY(kw IN $keywords WHERE toLower(c.name) CONTAINS toLower(kw))
        RETURN d.id AS id,
               d.name AS name,
               'Decision' AS node_type,
               d.content AS content,
               0.7 AS confidence
        LIMIT $limit
        """

        return await self._store.execute_read(
            query,
            {
                "tenant_id": tenant_id,
                "project_id": project_id,
                "keywords": topic_keywords,
                "limit": limit,
            },
        )
