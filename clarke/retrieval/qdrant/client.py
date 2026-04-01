"""Qdrant client wrapper with singleton lifecycle."""

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance,
    PointStruct,
    TextIndexParams,
    VectorParams,
)

from clarke.settings import EmbeddingSettings, RetrievalSettings
from clarke.telemetry.logging import get_logger

logger = get_logger(__name__)


class QdrantStore:
    def __init__(self, settings: RetrievalSettings, embedding_settings: EmbeddingSettings) -> None:
        self._settings = settings
        self._embedding_settings = embedding_settings
        self._client: AsyncQdrantClient | None = None

    async def connect(self) -> None:
        """Initialize async client and ensure collection exists."""
        self._client = AsyncQdrantClient(
            host=self._settings.qdrant_host,
            port=self._settings.qdrant_port,
            api_key=self._settings.qdrant_api_key or None,
        )
        await self.ensure_collection()

    async def ensure_collection(self) -> None:
        """Create collection if it doesn't exist."""
        if not self._client:
            return
        collections = await self._client.get_collections()
        names = [c.name for c in collections.collections]
        if self._settings.qdrant_collection not in names:
            await self._client.create_collection(
                collection_name=self._settings.qdrant_collection,
                vectors_config=VectorParams(
                    size=self._embedding_settings.embedding_dimensions,
                    distance=Distance.COSINE,
                ),
            )
            logger.info(
                "qdrant_collection_created",
                collection=self._settings.qdrant_collection,
            )
        # Ensure text index on content field for hybrid BM25 search
        import contextlib

        with contextlib.suppress(Exception):
            await self._client.create_payload_index(
                collection_name=self._settings.qdrant_collection,
                field_name="content",
                field_schema=TextIndexParams(
                    type="text",
                    tokenizer="word",
                    min_token_len=3,
                    max_token_len=20,
                ),
            )

    async def upsert_chunks(
        self,
        chunk_ids: list[str],
        vectors: list[list[float]],
        payloads: list[dict],
    ) -> None:
        """Upsert points with payload."""
        if not self._client:
            raise RuntimeError("Qdrant client not connected")
        points = [
            PointStruct(id=cid, vector=vec, payload=payload)
            for cid, vec, payload in zip(chunk_ids, vectors, payloads, strict=True)
        ]
        await self._client.upsert(
            collection_name=self._settings.qdrant_collection,
            points=points,
        )

    async def delete_by_document(self, document_id: str) -> None:
        """Delete all points for a document (for re-ingestion)."""
        if not self._client:
            return
        from qdrant_client.models import FieldCondition, Filter, MatchValue

        await self._client.delete(
            collection_name=self._settings.qdrant_collection,
            points_selector=Filter(
                must=[FieldCondition(key="document_id", match=MatchValue(value=document_id))]
            ),
        )

    async def health_check(self) -> bool:
        """Return True if Qdrant is reachable."""
        if not self._client:
            return False
        try:
            await self._client.get_collections()
            return True
        except Exception:
            return False

    async def close(self) -> None:
        """Close the client connection."""
        if self._client:
            await self._client.close()
            self._client = None

    @property
    def client(self) -> AsyncQdrantClient:
        if not self._client:
            raise RuntimeError("Qdrant client not connected")
        return self._client

    @property
    def collection_name(self) -> str:
        return self._settings.qdrant_collection


# Module-level singleton
_store: QdrantStore | None = None


async def init_qdrant(retrieval: RetrievalSettings, embedding: EmbeddingSettings) -> None:
    global _store
    _store = QdrantStore(retrieval, embedding)
    try:
        await _store.connect()
        logger.info("qdrant_connected")
    except Exception:
        logger.warning("qdrant_connection_failed", exc_info=True)
        _store = None


async def dispose_qdrant() -> None:
    global _store
    if _store:
        await _store.close()
        _store = None


def get_qdrant_store() -> QdrantStore:
    if _store is None:
        raise RuntimeError("Qdrant not initialized. Call init_qdrant() first.")
    return _store
