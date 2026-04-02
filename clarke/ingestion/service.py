"""Ingestion service — orchestrates parse → redact → chunk → embed → index."""

from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from clarke.api.schemas.ingest import (
    DocumentStatusResponse,
    IngestDocumentRequest,
    IngestDocumentResponse,
)
from clarke.ingestion.chunking import chunk_sections
from clarke.ingestion.documents import parse_document
from clarke.ingestion.embeddings import embed_texts
from clarke.ingestion.redaction import redact
from clarke.retrieval.qdrant.client import get_qdrant_store
from clarke.settings import Settings
from clarke.storage.postgres.repositories.document_repo import (
    create_chunks,
    create_document,
    create_ingestion_job,
    get_chunk_count,
    get_document,
    update_document_status,
    update_ingestion_job,
)
from clarke.telemetry.logging import get_logger
from clarke.utils.time import utc_now

logger = get_logger(__name__)


class IngestionService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def ingest_document(
        self,
        request: IngestDocumentRequest,
        session: AsyncSession,
    ) -> IngestDocumentResponse:
        """Orchestrate full ingestion: parse → redact → chunk → embed → index."""
        doc_id = str(uuid4())
        job_id = str(uuid4())

        # Create document record
        await create_document(
            session,
            {
                "id": doc_id,
                "tenant_id": request.tenant_id,
                "project_id": request.project_id,
                "filename": request.filename,
                "content_type": request.content_type,
                "source_url": request.source_url,
                "status": "processing",
                "metadata_": request.metadata,
            },
        )

        # Create ingestion job
        await create_ingestion_job(
            session,
            {
                "id": job_id,
                "tenant_id": request.tenant_id,
                "document_id": doc_id,
                "status": "running",
            },
        )
        await session.commit()

        try:
            # Parse
            sections = parse_document(request.content, request.content_type)

            # Redact each section
            for section in sections:
                result = redact(section.content)
                section.content = result.content

            # Chunk
            model = self.settings.embedding.embedding_model
            chunks = chunk_sections(
                sections,
                document_id=doc_id,
                max_tokens=self.settings.embedding.chunk_size_tokens,
                overlap_tokens=self.settings.embedding.chunk_overlap_tokens,
                model=model,
            )

            if not chunks:
                await update_document_status(session, doc_id, "ready")
                await update_ingestion_job(session, job_id, "completed")
                await session.commit()
                return IngestDocumentResponse(document_id=doc_id, job_id=job_id, status="completed")

            # Save chunks to PostgreSQL
            chunk_records = []
            for chunk in chunks:
                chunk_id = str(uuid4())
                chunk.metadata["chunk_db_id"] = chunk_id
                chunk_records.append(
                    {
                        "id": chunk_id,
                        "document_id": doc_id,
                        "tenant_id": request.tenant_id,
                        "content": chunk.content,
                        "chunk_index": chunk.chunk_index,
                        "token_count": chunk.token_count,
                        "embedding_model": model,
                        "metadata_": chunk.metadata,
                    }
                )
            await create_chunks(session, chunk_records)

            # Embed
            texts = [c.content for c in chunks]
            vectors = await embed_texts(
                texts,
                model=model,
                dimensions=self.settings.embedding.embedding_dimensions,
            )

            # Index in Qdrant
            store = get_qdrant_store()
            chunk_ids = [r["id"] for r in chunk_records]
            is_skill = (request.metadata or {}).get("doc_type") == "skill"
            payloads = []
            for c in chunks:
                payload = {
                    "tenant_id": request.tenant_id,
                    "project_id": request.project_id,
                    "document_id": doc_id,
                    "chunk_index": c.chunk_index,
                    "content": c.content[:1000],
                    "section_heading": c.metadata.get("heading"),
                    "source_type": "skill" if is_skill else "docs",
                    "node_type": "chunk",
                    "trust_tier": 2 if is_skill else 3,
                    "embedding_version": model,
                    "sensitivity_tier": "internal",
                    "redaction_version": "v1",
                    "is_active": True,
                    "canonical_ref": doc_id,
                    "updated_at": utc_now().isoformat(),
                }
                if is_skill:
                    meta = request.metadata or {}
                    payload["skill_name"] = meta.get("skill_name", "")
                    payload["agent_capabilities"] = meta.get("agent_capabilities", [])
                    payload["priority"] = meta.get("priority", 1)
                    payload["trigger_conditions"] = meta.get("trigger_conditions", [])
                payloads.append(payload)
            await store.upsert_chunks(chunk_ids, vectors, payloads)

            # Build graph nodes (best-effort, non-blocking)
            try:
                from clarke.retrieval.neo4j.client import get_neo4j_store as get_neo4j

                get_neo4j()  # verify available
                from clarke.ingestion.graph_build import build_graph_nodes

                await build_graph_nodes(request.tenant_id, request.project_id, doc_id, chunks)
            except RuntimeError:
                logger.debug("graph_build_skipped", reason="neo4j not available")
            except Exception:
                logger.warning("graph_build_failed", document_id=doc_id, exc_info=True)

            # Update statuses
            await update_document_status(session, doc_id, "ready")
            await update_ingestion_job(session, job_id, "completed")

            # Audit
            from clarke.storage.postgres.repositories.audit_repo import create_audit_event

            await create_audit_event(
                session,
                tenant_id=request.tenant_id,
                actor_id="system",
                action="document_ingested",
                target_type="document",
                target_id=doc_id,
                metadata={"chunk_count": len(chunks), "filename": request.filename},
            )
            await session.commit()

            logger.info(
                "ingestion_completed",
                document_id=doc_id,
                chunk_count=len(chunks),
            )

            return IngestDocumentResponse(document_id=doc_id, job_id=job_id, status="completed")

        except Exception as e:
            logger.exception("ingestion_failed", document_id=doc_id)
            await update_document_status(session, doc_id, "error")
            await update_ingestion_job(session, job_id, "failed", error=str(e))
            await session.commit()
            raise

    async def get_document_status(
        self,
        document_id: str,
        session: AsyncSession,
    ) -> DocumentStatusResponse:
        """Get document metadata and chunk count."""
        doc = await get_document(session, document_id)
        if not doc:
            raise ValueError(f"Document {document_id} not found")

        chunk_count = await get_chunk_count(session, document_id)

        return DocumentStatusResponse(
            document_id=doc.id,
            filename=doc.filename,
            content_type=doc.content_type,
            status=doc.status,
            chunk_count=chunk_count,
            created_at=doc.created_at.isoformat(),
            metadata=doc.metadata_,
        )
