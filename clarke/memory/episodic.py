"""Episodic memory — classify, summarize, and index query/answer interactions.

Not every interaction is worth remembering. The significance classifier
separates signal (decisions, preferences, corrections, facts) from noise
(greetings, short acknowledgments, failed lookups).
"""

from clarke.ingestion.embeddings import embed_single
from clarke.ingestion.redaction import redact
from clarke.memory.significance import classify_significance
from clarke.settings import Settings
from clarke.telemetry.logging import get_logger

logger = get_logger(__name__)


def build_episodic_summary(
    message: str,
    answer: str,
    memory_type: str = "conversational",
    query_features: dict | None = None,
) -> str:
    """Build a typed summary of a query/answer interaction for episodic storage."""
    features_str = ""
    if query_features:
        keywords = query_features.get("keywords", [])
        if keywords:
            features_str = f" Topics: {', '.join(keywords[:5])}."

    type_prefix = {
        "decision": "DECISION:",
        "correction": "CORRECTION:",
        "preference": "USER PREFERENCE:",
        "factual": "FACT:",
        "conceptual": "DISCUSSION:",
        "bug_fix": "BUG FIX:",
        "code_pattern": "CODE PATTERN:",
    }.get(memory_type, "")

    if type_prefix:
        return f"{type_prefix} {message}\nAnswer: {answer[:500]}{features_str}"
    return f"User asked: {message}\nAnswer: {answer[:500]}{features_str}"


async def store_episodic_memory(
    tenant_id: str,
    project_id: str,
    user_id: str,
    session_id: str | None,
    request_id: str,
    message: str,
    answer: str,
    query_features: dict | None = None,
    settings: Settings | None = None,
    agent_profile_id: str | None = None,
) -> None:
    """Classify, summarize, redact, embed, and index a query/answer as episodic memory.

    Only stores interactions that pass significance classification.
    Significance score is stored in the payload to influence retrieval ranking.
    """
    if not settings:
        from clarke.settings import get_settings

        settings = get_settings()

    # Classify significance — skip noise
    sig = classify_significance(message, answer, query_features)

    if not sig.should_store:
        logger.debug(
            "episodic_memory_skipped",
            request_id=request_id,
            reason=sig.reason,
            score=sig.score,
            memory_type=sig.memory_type,
        )
        return

    # Build typed summary
    summary = build_episodic_summary(message, answer, sig.memory_type, query_features)

    # Redact PII
    redacted = redact(summary)

    # Embed
    try:
        vector = await embed_single(
            redacted.content,
            model=settings.embedding.embedding_model,
            dimensions=settings.embedding.embedding_dimensions,
        )
    except Exception:
        logger.warning("episodic_embedding_failed", request_id=request_id)
        return

    # Index in Qdrant with significance metadata
    try:
        from uuid import uuid4

        from clarke.retrieval.qdrant.client import get_qdrant_store

        store = get_qdrant_store()
        point_id = str(uuid4())
        await store.upsert_chunks(
            chunk_ids=[point_id],
            vectors=[vector],
            payloads=[
                {
                    "tenant_id": tenant_id,
                    "project_id": project_id,
                    "user_id": user_id,
                    "session_id": session_id,
                    "request_id": request_id,
                    "content": redacted.content,
                    "source_type": "memory",
                    "node_type": "episodic",
                    "memory_type": sig.memory_type,
                    "significance_score": sig.score,
                    "trust_tier": 4,  # episodic summary = tier 4
                    "embedding_version": settings.embedding.embedding_model,
                    "sensitivity_tier": "internal",
                    "redaction_version": "v1",
                    "is_active": True,
                    "canonical_ref": request_id,
                    "redacted_fields": redacted.redacted_fields,
                    "agent_profile_id": agent_profile_id,
                }
            ],
        )
        logger.info(
            "episodic_memory_stored",
            request_id=request_id,
            memory_type=sig.memory_type,
            significance=sig.score,
        )
    except RuntimeError:
        logger.debug("episodic_store_skipped", reason="qdrant not available")
    except Exception:
        logger.warning("episodic_store_failed", request_id=request_id, exc_info=True)
